"""Catalog API — products, varieties, grades, FOB prices, freight, CIF calculator."""
import csv
import io
import uuid
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.catalog import (
    FobPrice, FreightRate, Port, Product, ProductGrade,
    ProductVariety, TenantDefaults,
)
from app.models.commodity_ref import CommodityReference
from app.schemas.catalog import (
    CfrCalculateRequest, CfrCalculateResponse,
    FobPriceBulkCreate, FobPriceCreate, FobPriceResponse,
    FreightRateCreate, FreightRateResponse,
    PortResponse, ProductCreate, ProductResponse, ProductUpdate,
    GradeResponse, VarietyResponse,
    TenantDefaultsResponse, TenantDefaultsUpdate,
)

logger = get_logger("api.catalog")
router = APIRouter(prefix="/catalog", tags=["catalog"])


# ─── Ports ────────────────────────────────────────────────────────────

@router.get("/ports", response_model=list)
async def list_ports(
    db: AsyncSession = Depends(get_db),
    country: Optional[str] = None,
    search: Optional[str] = None,
):
    """List ports. Public — no auth needed for port lookup."""
    query = select(Port).where(Port.is_active.is_(True))
    if country:
        query = query.where(Port.country.ilike(f"%{country}%"))
    if search:
        query = query.where(Port.name.ilike(f"%{search}%"))
    query = query.order_by(Port.country, Port.name)
    result = await db.execute(query)
    return [
        PortResponse(id=str(p.id), name=p.name, code=p.code, city=p.city, country=p.country)
        for p in result.scalars().all()
    ]


# ─── Commodity Reference (search/autocomplete) ───────────────────────

@router.get("/commodities/search")
async def search_commodities(
    q: str = Query("", min_length=1),
    db: AsyncSession = Depends(get_db),
):
    """Search commodity reference data for autocomplete. Public, no auth."""
    query = select(CommodityReference).where(
        CommodityReference.is_active.is_(True),
        CommodityReference.name.ilike(f"%{q}%"),
    ).order_by(CommodityReference.name).limit(10)
    result = await db.execute(query)
    return [
        {
            "name": c.name,
            "hs_codes": c.hs_codes or [],
            "aliases": c.aliases or [],
            "category": c.category,
            "default_capacity_20ft_mt": c.default_capacity_20ft_mt,
            "default_capacity_40ft_mt": c.default_capacity_40ft_mt,
        }
        for c in result.scalars().all()
    ]


# ─── Products ─────────────────────────────────────────────────────────

def _product_response(p: Product) -> ProductResponse:
    return ProductResponse(
        id=str(p.id), tenant_id=str(p.tenant_id),
        name=p.name, origin_country=p.origin_country,
        hs_code=p.hs_code, description=p.description,
        is_active=p.is_active,
        varieties=[
            VarietyResponse(
                id=str(v.id), name=v.name, is_active=v.is_active,
                grades=[
                    GradeResponse(id=str(g.id), name=g.name, specifications=g.specifications, is_active=g.is_active)
                    for g in (v.grades or [])
                ],
            )
            for v in (p.varieties or [])
        ],
        created_at=p.created_at.isoformat(),
    )


@router.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(
    body: ProductCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    product = Product(
        tenant_id=tenant_id, name=body.name,
        origin_country=body.origin_country,
        hs_code=body.hs_code, description=body.description,
        default_loading_port_id=body.default_loading_port_id,
        shelf_life_days=body.shelf_life_days,
        certifications=body.certifications,
        aliases=body.aliases,
        capacity_20ft_mt=body.capacity_20ft_mt,
        capacity_40ft_mt=body.capacity_40ft_mt,
        capacity_40ft_hc_mt=body.capacity_40ft_hc_mt,
    )
    db.add(product)
    await db.flush()

    for v in body.varieties:
        variety = ProductVariety(
            product_id=product.id, tenant_id=tenant_id, name=v.name,
        )
        db.add(variety)
        await db.flush()
        for g in v.grades:
            db.add(ProductGrade(
                variety_id=variety.id, tenant_id=tenant_id,
                name=g.name, specifications=g.specifications,
                packaging_type=g.packaging_type,
                packaging_weight_kg=g.packaging_weight_kg,
                moq_mt=g.moq_mt,
            ))

    await db.commit()
    await db.refresh(product)
    logger.info("Product created: id=%s name=%s tenant=%s", product.id, product.name, tenant_id)
    return _product_response(product)


@router.get("/products", response_model=list)
async def list_products(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(
            Product.tenant_id == tenant_id, Product.is_active.is_(True),
        ).order_by(Product.name)
    )
    return [_product_response(p) for p in result.scalars().all()]


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _product_response(product)


@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: uuid.UUID, body: ProductUpdate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return _product_response(product)


@router.delete("/products/{product_id}", status_code=204)
async def delete_product(
    product_id: uuid.UUID,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.tenant_id == tenant_id)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product.is_active = False
    await db.commit()
    logger.info("Product deactivated: id=%s name=%s tenant=%s", product_id, product.name, tenant_id)


@router.post("/products/{product_id}/varieties", status_code=201)
async def add_variety(
    product_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    name: str = Query(...),
):
    variety = ProductVariety(product_id=product_id, tenant_id=tenant_id, name=name)
    db.add(variety)
    await db.commit()
    await db.refresh(variety)
    return {"id": str(variety.id), "name": variety.name}


@router.post("/varieties/{variety_id}/grades", status_code=201)
async def add_grade(
    variety_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    name: str = Query(...),
):
    grade = ProductGrade(variety_id=variety_id, tenant_id=tenant_id, name=name)
    db.add(grade)
    await db.commit()
    await db.refresh(grade)
    return {"id": str(grade.id), "name": grade.name}


# ─── CSV Templates & Import ──────────────────────────────────────────

@router.get("/products/template/download")
async def download_product_template():
    """Download CSV template for bulk product upload. HS codes are text to preserve leading zeros."""
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_ALL)
    writer.writerow(["product_name", "origin_country", "variety", "grade", "hs_code", "description"])
    writer.writerow(["Black Pepper", "India", "Malabar", "500GL", "0904.11", "Premium quality"])
    writer.writerow(["Black Pepper", "India", "Malabar", "550GL", "0904.11", ""])
    writer.writerow(["Black Pepper", "India", "Tellicherry", "TGSEB", "0904.11", ""])
    writer.writerow(["Vanilla Sticks", "India", "Planifolia", "Grade A", "0905.10", ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=product_catalog_template.csv"},
    )


@router.post("/products/import", status_code=201)
async def import_products(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
):
    """Import products from CSV. Groups by product_name + origin_country → variety → grade."""
    content = await file.read()
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    products_created = 0
    varieties_created = 0
    grades_created = 0

    # Group rows: product_name+origin → varieties → grades
    product_cache = {}  # (name, origin) → Product
    variety_cache = {}  # (product_id, variety_name) → ProductVariety

    for row in reader:
        pname = row.get("product_name", "").strip()
        origin = row.get("origin_country", "").strip()
        vname = row.get("variety", "").strip()
        gname = row.get("grade", "").strip()

        if not pname or not origin:
            continue

        # Get or create product
        pkey = (pname.lower(), origin.lower())
        if pkey not in product_cache:
            existing = await db.execute(
                select(Product).where(
                    Product.tenant_id == tenant_id,
                    Product.name.ilike(pname),
                    Product.origin_country.ilike(origin),
                )
            )
            product = existing.scalar_one_or_none()
            if not product:
                product = Product(
                    tenant_id=tenant_id, name=pname, origin_country=origin,
                    hs_code=row.get("hs_code", "").strip() or None,
                    description=row.get("description", "").strip() or None,
                )
                db.add(product)
                await db.flush()
                products_created += 1
            product_cache[pkey] = product

        product = product_cache[pkey]

        # Get or create variety
        if vname:
            vkey = (product.id, vname.lower())
            if vkey not in variety_cache:
                existing_v = await db.execute(
                    select(ProductVariety).where(
                        ProductVariety.product_id == product.id,
                        ProductVariety.name.ilike(vname),
                    )
                )
                variety = existing_v.scalar_one_or_none()
                if not variety:
                    variety = ProductVariety(
                        product_id=product.id, tenant_id=tenant_id, name=vname,
                    )
                    db.add(variety)
                    await db.flush()
                    varieties_created += 1
                variety_cache[vkey] = variety

            variety = variety_cache[vkey]

            # Create grade
            if gname:
                existing_g = await db.execute(
                    select(ProductGrade).where(
                        ProductGrade.variety_id == variety.id,
                        ProductGrade.name.ilike(gname),
                    )
                )
                if not existing_g.scalar_one_or_none():
                    db.add(ProductGrade(
                        variety_id=variety.id, tenant_id=tenant_id, name=gname,
                    ))
                    grades_created += 1

    await db.commit()
    logger.info(
        "Catalog import: tenant=%s products=%d varieties=%d grades=%d",
        tenant_id, products_created, varieties_created, grades_created,
    )
    return {
        "products_created": products_created,
        "varieties_created": varieties_created,
        "grades_created": grades_created,
    }


# ─── FOB Prices ──────────────────────────────────────────────────────

@router.post("/prices/fob", response_model=FobPriceResponse, status_code=201)
async def create_fob_price(
    body: FobPriceCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    price = FobPrice(
        tenant_id=tenant_id, grade_id=body.grade_id,
        origin_port_id=body.origin_port_id, price_date=body.price_date,
        price_usd_per_kg=body.price_usd_per_kg,
        price_usd_per_mt=body.price_usd_per_mt,
        currency=body.currency, notes=body.notes,
    )
    db.add(price)
    await db.commit()
    await db.refresh(price)
    logger.info("FOB price created: grade=%s date=%s tenant=%s", body.grade_id, body.price_date, tenant_id)
    return await _fob_price_response(db, price)


@router.post("/prices/fob/bulk", status_code=201)
async def create_fob_prices_bulk(
    body: FobPriceBulkCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Create multiple FOB prices at once (for daily price updates)."""
    created = 0
    for p in body.prices:
        price = FobPrice(
            tenant_id=tenant_id, grade_id=p.grade_id,
            origin_port_id=p.origin_port_id, price_date=p.price_date,
            price_usd_per_kg=p.price_usd_per_kg,
            price_usd_per_mt=p.price_usd_per_mt,
            currency=p.currency, notes=p.notes,
        )
        db.add(price)
        created += 1
    await db.commit()
    logger.info("FOB prices bulk created: count=%d tenant=%s", created, tenant_id)
    return {"created": created}


@router.get("/prices/fob", response_model=list)
async def list_fob_prices(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    grade_id: Optional[uuid.UUID] = None,
    price_date: Optional[date] = None,
    limit: int = Query(50, ge=1, le=200),
):
    query = select(FobPrice).where(FobPrice.tenant_id == tenant_id)
    if grade_id:
        query = query.where(FobPrice.grade_id == grade_id)
    if price_date:
        query = query.where(FobPrice.price_date == price_date)
    query = query.order_by(desc(FobPrice.price_date)).limit(limit)

    result = await db.execute(query)
    return [await _fob_price_response(db, p) for p in result.scalars().all()]


async def _fob_price_response(db: AsyncSession, p: FobPrice) -> FobPriceResponse:
    grade = (await db.execute(select(ProductGrade).where(ProductGrade.id == p.grade_id))).scalar_one_or_none()
    variety = None
    product = None
    if grade:
        variety = (await db.execute(select(ProductVariety).where(ProductVariety.id == grade.variety_id))).scalar_one_or_none()
        if variety:
            product = (await db.execute(select(Product).where(Product.id == variety.product_id))).scalar_one_or_none()
    port = (await db.execute(select(Port).where(Port.id == p.origin_port_id))).scalar_one_or_none()

    return FobPriceResponse(
        id=str(p.id), grade_id=str(p.grade_id),
        grade_name=grade.name if grade else None,
        product_name=product.name if product else None,
        variety_name=variety.name if variety else None,
        origin_port_id=str(p.origin_port_id),
        origin_port_name=port.name if port else None,
        price_date=p.price_date.isoformat(),
        price_usd_per_kg=float(p.price_usd_per_kg) if p.price_usd_per_kg else None,
        price_usd_per_mt=float(p.price_usd_per_mt) if p.price_usd_per_mt else None,
        currency=p.currency, notes=p.notes,
    )


# ─── Freight Rates ───────────────────────────────────────────────────

@router.post("/freight", response_model=FreightRateResponse, status_code=201)
async def create_freight_rate(
    body: FreightRateCreate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    rate = FreightRate(
        tenant_id=tenant_id,
        origin_port_id=body.origin_port_id,
        destination_port_id=body.destination_port_id,
        container_type=body.container_type,
        rate_usd=body.rate_usd, transit_days=body.transit_days,
        valid_from=body.valid_from, valid_until=body.valid_until,
        notes=body.notes,
    )
    db.add(rate)
    await db.commit()
    await db.refresh(rate)
    logger.info("Freight rate created: %s → %s tenant=%s", body.origin_port_id, body.destination_port_id, tenant_id)
    return await _freight_response(db, rate)


@router.get("/freight", response_model=list)
async def list_freight_rates(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    origin_port_id: Optional[uuid.UUID] = None,
    destination_port_id: Optional[uuid.UUID] = None,
):
    query = select(FreightRate).where(FreightRate.tenant_id == tenant_id)
    if origin_port_id:
        query = query.where(FreightRate.origin_port_id == origin_port_id)
    if destination_port_id:
        query = query.where(FreightRate.destination_port_id == destination_port_id)
    result = await db.execute(query)
    return [await _freight_response(db, r) for r in result.scalars().all()]


async def _freight_response(db: AsyncSession, r: FreightRate) -> FreightRateResponse:
    op = (await db.execute(select(Port).where(Port.id == r.origin_port_id))).scalar_one_or_none()
    dp = (await db.execute(select(Port).where(Port.id == r.destination_port_id))).scalar_one_or_none()
    return FreightRateResponse(
        id=str(r.id),
        origin_port_name=op.name if op else None,
        origin_port_country=op.country if op else None,
        destination_port_name=dp.name if dp else None,
        destination_port_country=dp.country if dp else None,
        container_type=r.container_type,
        rate_usd=float(r.rate_usd) if r.rate_usd else None,
        transit_days=r.transit_days,
        valid_from=r.valid_from.isoformat() if r.valid_from else None,
        valid_until=r.valid_until.isoformat() if r.valid_until else None,
        notes=r.notes,
    )


# ─── Tenant Defaults ─────────────────────────────────────────────────

@router.get("/defaults", response_model=TenantDefaultsResponse)
async def get_defaults(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TenantDefaults).where(TenantDefaults.tenant_id == tenant_id)
    )
    defaults = result.scalar_one_or_none()
    if not defaults:
        return TenantDefaultsResponse()

    port = None
    if defaults.default_origin_port_id:
        port = (await db.execute(select(Port).where(Port.id == defaults.default_origin_port_id))).scalar_one_or_none()

    return TenantDefaultsResponse(
        default_origin_port_id=str(defaults.default_origin_port_id) if defaults.default_origin_port_id else None,
        default_origin_port_name=port.name if port else None,
        default_currency=defaults.default_currency,
        default_container_type=defaults.default_container_type,
        default_payment_terms=defaults.default_payment_terms,
        custom_settings=defaults.custom_settings,
    )


@router.put("/defaults", response_model=TenantDefaultsResponse)
async def update_defaults(
    body: TenantDefaultsUpdate,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TenantDefaults).where(TenantDefaults.tenant_id == tenant_id)
    )
    defaults = result.scalar_one_or_none()

    if not defaults:
        defaults = TenantDefaults(tenant_id=tenant_id)
        db.add(defaults)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(defaults, field, value)

    await db.commit()
    await db.refresh(defaults)
    logger.info("Tenant defaults updated: tenant=%s", tenant_id)

    port = None
    if defaults.default_origin_port_id:
        port = (await db.execute(select(Port).where(Port.id == defaults.default_origin_port_id))).scalar_one_or_none()

    return TenantDefaultsResponse(
        default_origin_port_id=str(defaults.default_origin_port_id) if defaults.default_origin_port_id else None,
        default_origin_port_name=port.name if port else None,
        default_currency=defaults.default_currency,
        default_container_type=defaults.default_container_type,
        default_payment_terms=defaults.default_payment_terms,
        custom_settings=defaults.custom_settings,
    )


# ─── CFR Calculator ──────────────────────────────────────────────────

@router.post("/cfr/calculate", response_model=CfrCalculateResponse)
async def calculate_cif(
    body: CfrCalculateRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Calculate CFR price = FOB + Freight. Auto-resolves ports if not specified."""
    try:
        return await _calculate_cfr(body, tenant_id, db)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("CFR calculation failed: tenant=%s error=%s", tenant_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="CFR calculation failed. Check your pricing and freight data.")


async def _calculate_cfr(body: CfrCalculateRequest, tenant_id, db: AsyncSession):
    # Resolve origin port (use default if not provided)
    origin_port_id = body.origin_port_id
    if not origin_port_id:
        defaults = (await db.execute(
            select(TenantDefaults).where(TenantDefaults.tenant_id == tenant_id)
        )).scalar_one_or_none()
        if defaults and defaults.default_origin_port_id:
            origin_port_id = defaults.default_origin_port_id
        else:
            raise HTTPException(status_code=400, detail="No origin port specified and no default set")

    # Get latest FOB price for the grade
    fob_query = select(FobPrice).where(
        FobPrice.tenant_id == tenant_id,
        FobPrice.grade_id == body.grade_id,
        FobPrice.origin_port_id == origin_port_id,
    ).order_by(desc(FobPrice.price_date))

    if body.price_date:
        fob_query = fob_query.where(FobPrice.price_date <= body.price_date)

    fob = (await db.execute(fob_query.limit(1))).scalar_one_or_none()

    # Get freight rate
    freight = (await db.execute(
        select(FreightRate).where(
            FreightRate.tenant_id == tenant_id,
            FreightRate.origin_port_id == origin_port_id,
            FreightRate.destination_port_id == body.destination_port_id,
            FreightRate.container_type == body.container_type,
        ).limit(1)
    )).scalar_one_or_none()

    # Resolve names
    grade = (await db.execute(select(ProductGrade).where(ProductGrade.id == body.grade_id))).scalar_one_or_none()
    variety = (await db.execute(select(ProductVariety).where(ProductVariety.id == grade.variety_id))).scalar_one_or_none() if grade else None
    product = (await db.execute(select(Product).where(Product.id == variety.product_id))).scalar_one_or_none() if variety else None
    op = (await db.execute(select(Port).where(Port.id == origin_port_id))).scalar_one_or_none()
    dp = (await db.execute(select(Port).where(Port.id == body.destination_port_id))).scalar_one_or_none()

    fob_per_mt = float(fob.price_usd_per_mt) if fob and fob.price_usd_per_mt else None
    if not fob_per_mt and fob and fob.price_usd_per_kg:
        fob_per_mt = float(fob.price_usd_per_kg) * 1000

    # Resolve container capacity — use product-level if set, else system defaults
    system_defaults = {"20ft": 18, "40ft": 26, "40ft_hc": 28}
    container_capacity = system_defaults.get(body.container_type, 18)
    if product:
        product_capacity = {
            "20ft": float(product.capacity_20ft_mt) if product.capacity_20ft_mt else None,
            "40ft": float(product.capacity_40ft_mt) if product.capacity_40ft_mt else None,
            "40ft_hc": float(product.capacity_40ft_hc_mt) if product.capacity_40ft_hc_mt else None,
        }
        if product_capacity.get(body.container_type):
            container_capacity = product_capacity[body.container_type]

    # Freight per MT
    freight_per_mt = None
    freight_per_container = None
    if freight and freight.rate_usd:
        freight_per_container = float(freight.rate_usd)
        freight_per_mt = freight_per_container / container_capacity

    fob_per_mt = float(fob.price_usd_per_mt) if fob and fob.price_usd_per_mt else None
    if not fob_per_mt and fob and fob.price_usd_per_kg:
        fob_per_mt = float(fob.price_usd_per_kg) * 1000

    cif_per_mt = None
    total = None
    notes = []
    if fob_per_mt and freight_per_mt:
        cif_per_mt = round(fob_per_mt + freight_per_mt, 2)
        total = round(cif_per_mt * body.quantity_mt, 2)
    elif fob_per_mt:
        notes.append("Freight rate not found for this route")
    elif freight_per_mt:
        notes.append("FOB price not found for this grade/date")
    else:
        notes.append("Neither FOB price nor freight rate found")

    return CfrCalculateResponse(
        fob_price_per_mt=fob_per_mt,
        freight_per_container=freight_per_container,
        freight_per_mt=round(freight_per_mt, 2) if freight_per_mt else None,
        cfr_price_per_mt=cif_per_mt,
        total_value=total,
        origin_port=op.name if op else None,
        destination_port=dp.name if dp else None,
        product=product.name if product else None,
        variety=variety.name if variety else None,
        grade=grade.name if grade else None,
        price_date=fob.price_date.isoformat() if fob else None,
        container_type=body.container_type,
        container_capacity_mt=container_capacity,
        quantity_mt=body.quantity_mt,
        packaging=grade.packaging_type if grade else None,
        moq_mt=float(grade.moq_mt) if grade and grade.moq_mt else None,
        notes="; ".join(notes) if notes else None,
    )
