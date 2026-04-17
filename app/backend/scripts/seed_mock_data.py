"""Seed mock companies, contacts, leads, ports, and shipments for testing."""
import asyncio
import random
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

# Ensure app modules are importable
import sys
sys.path.insert(0, ".")

from app.database import AsyncSessionLocal
from app.models.tenant import Tenant
from app.models.company import Company
from app.models.contact import Contact
from app.models.leads import InboundLead
from app.models.catalog import Port, Product
from app.models.email_account import EmailAccount
from app.models.shipment import Shipment
from app.models.enums import CompanySource, ContactSource, ShipmentDirection


PORTS_SEED = [
    {"name": "Cochin", "code": "INCOK", "city": "Kochi", "country": "India"},
    {"name": "Tuticorin", "code": "INTUT", "city": "Thoothukudi", "country": "India"},
    {"name": "Mumbai JNPT", "code": "INNSA", "city": "Mumbai", "country": "India"},
    {"name": "Jebel Ali", "code": "AEJEA", "city": "Dubai", "country": "UAE"},
    {"name": "Hamburg", "code": "DEHAM", "city": "Hamburg", "country": "Germany"},
    {"name": "Singapore PSA", "code": "SGSIN", "city": "Singapore", "country": "Singapore"},
    {"name": "Rotterdam", "code": "NLRTM", "city": "Rotterdam", "country": "Netherlands"},
    {"name": "Felixstowe", "code": "GBFXT", "city": "Felixstowe", "country": "United Kingdom"},
]


async def seed():
    async with AsyncSessionLocal() as db:
        tenant = (await db.execute(select(Tenant).limit(1))).scalar_one_or_none()
        if not tenant:
            print("ERROR: No tenant found. Run the app first to create a tenant.")
            return

        tenant_id = tenant.id
        print(f"Seeding for tenant: {tenant.company_name} (id={str(tenant_id)[:8]})")

        # ── Ports ────────────────────────────────────────────────────
        existing_ports = (await db.execute(select(Port))).scalars().all()
        port_map = {p.name: p for p in existing_ports}

        for ps in PORTS_SEED:
            if ps["name"] not in port_map:
                p = Port(name=ps["name"], code=ps["code"], city=ps["city"], country=ps["country"])
                db.add(p)
                port_map[ps["name"]] = p
                print(f"  Port: {ps['name']} ({ps['code']})")

        await db.flush()
        # Refresh port references
        for ps in PORTS_SEED:
            if not port_map[ps["name"]].id:
                await db.refresh(port_map[ps["name"]])

        cochin = port_map["Cochin"]
        tuticorin = port_map["Tuticorin"]
        jebel_ali = port_map["Jebel Ali"]
        hamburg = port_map["Hamburg"]
        singapore = port_map["Singapore PSA"]

        # ── Products (get existing) ──────────────────────────────────
        products = (await db.execute(select(Product).where(Product.tenant_id == tenant_id))).scalars().all()
        product_map = {p.name.lower(): p for p in products}
        print(f"  Found {len(products)} catalog products")

        # ── Companies ────────────────────────────────────────────────
        # Check existing
        existing_companies = (await db.execute(
            select(Company).where(Company.tenant_id == tenant_id, Company.name.in_(["Al Noor Trading LLC", "Hamburg Spice GmbH", "Savory Foods Pte Ltd"]))
        )).scalars().all()
        if existing_companies:
            print(f"  {len(existing_companies)} mock companies already exist. Skipping company/contact creation.")
            company_map = {c.name: c for c in existing_companies}
        else:
            # Company 1: Al Noor Trading LLC
            c1 = Company(
                tenant_id=tenant_id, name="Al Noor Trading LLC",
                country="UAE", city="Dubai", company_type="importer",
                rating="hot", source=CompanySource.manual,
                commodities=["Black Pepper"],
                destination_ports=["Jebel Ali"],
                import_volume_annual=720, shipment_frequency="monthly",
                phone="+971-4-555-1234", email="info@alnoortrading.ae",
                website="https://alnoortrading.ae",
                industry="spices & condiments",
                preferred_incoterms="CIF", preferred_payment_terms="LC at Sight",
                number_of_employees="51-200", year_established=2008,
                description="One of UAE's largest spice importers, supplying to retail chains and foodservice across the Middle East.",
            )
            # Company 2: Hamburg Spice GmbH
            c2 = Company(
                tenant_id=tenant_id, name="Hamburg Spice GmbH",
                country="Germany", city="Hamburg", company_type="distributor",
                rating="warm", source=CompanySource.discovery,
                commodities=["Black Pepper"],
                destination_ports=["Hamburg"],
                import_volume_annual=400, shipment_frequency="quarterly",
                phone="+49-40-555-6789", email="einkauf@hamburgspice.de",
                website="https://hamburgspice.de",
                industry="food ingredients",
                preferred_incoterms="CFR", preferred_payment_terms="CAD",
                number_of_employees="11-50", year_established=1995,
                description="German distributor of specialty spices for EU food manufacturers and retailers.",
            )
            # Company 3: Savory Foods Pte Ltd
            c3 = Company(
                tenant_id=tenant_id, name="Savory Foods Pte Ltd",
                country="Singapore", city="Singapore", company_type="re-exporter",
                rating="warm", source=CompanySource.discovery,
                commodities=["Black Pepper"],
                destination_ports=["Singapore PSA"],
                import_volume_annual=250, shipment_frequency="biannual",
                phone="+65-6555-1234", email="procurement@savoryfoods.sg",
                industry="food & beverage",
                preferred_incoterms="FOB", preferred_payment_terms="TT Advance",
                number_of_employees="11-50", year_established=2012,
                description="Singapore-based re-exporter sourcing from India for SE Asian markets.",
            )
            db.add_all([c1, c2, c3])
            await db.flush()
            for c in [c1, c2, c3]:
                await db.refresh(c)
            company_map = {"Al Noor Trading LLC": c1, "Hamburg Spice GmbH": c2, "Savory Foods Pte Ltd": c3}
            print("  Created 3 mock companies")

            # ── Contacts ─────────────────────────────────────────────
            ct1 = Contact(
                tenant_id=tenant_id, name="Ahmad Khan",
                salutation="Mr", email="ahmad@alnoortrading.ae",
                phone="+971-50-123-4567", whatsapp_number="+971501234567",
                company_name="Al Noor Trading LLC", company_id=c1.id,
                title="Head of Procurement", department="Procurement",
                country="UAE", city="Dubai",
                is_decision_maker=True, source=ContactSource.manual,
                preferred_channel="whatsapp", preferred_language="en",
            )
            ct2 = Contact(
                tenant_id=tenant_id, name="Klaus Weber",
                salutation="Mr", email="klaus@hamburgspice.de",
                phone="+49-170-987-6543", whatsapp_number="+491709876543",
                company_name="Hamburg Spice GmbH", company_id=c2.id,
                title="Purchasing Manager", department="Procurement",
                country="Germany", city="Hamburg",
                is_decision_maker=True, source=ContactSource.discovery,
                preferred_channel="email", preferred_language="en",
            )
            ct3 = Contact(
                tenant_id=tenant_id, name="Mei Lin Tan",
                salutation="Ms", email="meilan@savoryfoods.sg",
                phone="+65-9123-4567", whatsapp_number="+6591234567",
                company_name="Savory Foods Pte Ltd", company_id=c3.id,
                title="Director", department="Trading",
                country="Singapore", city="Singapore",
                is_decision_maker=True, source=ContactSource.discovery,
                preferred_channel="email", preferred_language="en",
            )
            db.add_all([ct1, ct2, ct3])
            await db.flush()
            print("  Created 3 mock contacts")

            # ── Leads ────────────────────────────────────────────────
            # Get or create a placeholder email account for leads
            email_acct = (await db.execute(select(EmailAccount).where(EmailAccount.tenant_id == tenant_id).limit(1))).scalar_one_or_none()
            if not email_acct:
                email_acct = EmailAccount(tenant_id=tenant_id, email_address="mock@tradecrm.example", provider="gmail")
                db.add(email_acct)
                await db.flush()
                await db.refresh(email_acct)

            lead1 = InboundLead(
                tenant_id=tenant_id,
                email_account_id=email_acct.id,
                gmail_message_id=f"mock_msg_{uuid.uuid4().hex[:12]}",
                gmail_thread_id=f"mock_thread_{uuid.uuid4().hex[:12]}",
                classification="lead", confidence=0.92,
                sender_name="Ahmad Khan", sender_email="ahmad@alnoortrading.ae",
                sender_phone="+971-50-123-4567",
                sender_company="Al Noor Trading LLC",
                sender_designation="Head of Procurement",
                subject="Inquiry: Malabar Black Pepper 550GL — 50 MT for Jebel Ali",
                body_preview="Dear Sir, We are interested in procuring 50 MT of Malabar Black Pepper 550GL grade, CIF Jebel Ali. Please share your best pricing and availability for shipment in May 2026.",
                body_full="Dear Sir,\n\nWe are interested in procuring 50 MT of Malabar Black Pepper 550GL grade, CIF Jebel Ali. Please share your best pricing and availability for shipment in May 2026.\n\nWe are a regular buyer and have been importing from Kerala origin for the past 5 years.\n\nPlease also share:\n- Certificate of Origin\n- Phytosanitary certificate\n- SGS inspection report\n\nLooking forward to your quotation.\n\nBest regards,\nAhmad Khan\nHead of Procurement\nAl Noor Trading LLC",
                products_mentioned=[{"raw": "Malabar Black Pepper 550GL", "matched_product_name": "Black Pepper"}],
                quantities=[{"value": 50, "unit": "MT"}],
                target_price=None,
                delivery_terms="CIF",
                destination="Jebel Ali",
                urgency="normal",
                language="en",
                thread_message_count=1,
                status="new",
                company_id=c1.id,
                contact_id=ct1.id,
            )
            lead2 = InboundLead(
                tenant_id=tenant_id,
                email_account_id=email_acct.id,
                gmail_message_id=f"mock_msg_{uuid.uuid4().hex[:12]}",
                gmail_thread_id=f"mock_thread_{uuid.uuid4().hex[:12]}",
                classification="lead", confidence=0.85,
                sender_name="Klaus Weber", sender_email="klaus@hamburgspice.de",
                sender_company="Hamburg Spice GmbH",
                sender_designation="Purchasing Manager",
                subject="Re: Black Pepper Tellicherry pricing and certifications",
                body_preview="Hello, following up on our discussion at the SIAL trade show. We are looking for Black Pepper Tellicherry TGSEB, 20 MT quarterly supply to Hamburg.",
                body_full="Hello,\n\nFollowing up on our discussion at the SIAL trade show. We are looking for Black Pepper Tellicherry TGSEB grade, approximately 20 MT per quarter for delivery to Hamburg.\n\nWe require:\n- EU organic certification\n- HACCP compliance\n- Consistent quality across shipments\n\nOur current supplier has had quality issues. We would like to trial Indian origin.\n\nPlease send your best FOB Cochin price and sample availability.\n\nRegards,\nKlaus Weber\nHamburg Spice GmbH",
                products_mentioned=[{"raw": "Black Pepper Tellicherry TGSEB", "matched_product_name": "Black Pepper"}],
                quantities=[{"value": 20, "unit": "MT"}],
                target_price=None,
                delivery_terms="FOB",
                destination="Hamburg",
                urgency="normal",
                language="en",
                thread_message_count=3,
                status="new",
                company_id=c2.id,
                contact_id=ct2.id,
            )
            db.add_all([lead1, lead2])
            await db.flush()
            print("  Created 2 mock leads")

        # ── Shipments ────────────────────────────────────────────────
        existing_shipments = (await db.execute(
            select(Shipment).where(Shipment.tenant_id == tenant_id).limit(1)
        )).scalar_one_or_none()
        if existing_shipments:
            print("  Shipments already exist. Skipping.")
        else:
            c1 = company_map.get("Al Noor Trading LLC")
            c2 = company_map.get("Hamburg Spice GmbH")
            c3 = company_map.get("Savory Foods Pte Ltd")

            shipments = []
            today = date.today()

            # Al Noor: 25 monthly Black Pepper imports from Cochin → Jebel Ali
            if c1:
                for i in range(25):
                    ship_date = today - timedelta(days=30 * i + random.randint(0, 10))
                    vol = round(random.uniform(15, 30), 2)
                    price = round(random.uniform(4900, 5400), 2)
                    shipments.append(Shipment(
                        tenant_id=tenant_id, company_id=c1.id,
                        source_id=f"TG-ALNOOR-{i+1:04d}",
                        source_provider="tradecrm_internal",
                        shipment_date=ship_date,
                        direction=ShipmentDirection.import_,
                        commodity_text="Black Pepper ASTA 550GL",
                        hs_code="090411",
                        origin_country="India", destination_country="UAE",
                        origin_port_id=cochin.id, destination_port_id=jebel_ali.id,
                        origin_port_text="Cochin", destination_port_text="Jebel Ali",
                        volume_mt=vol,
                        unit_price_usd_per_mt=price,
                        value_usd=round(vol * price, 2),
                        trade_partner_name=tenant.company_name,
                        trade_partner_country="India",
                    ))

            # Hamburg Spice: 8 Black Pepper + 4 Cardamom from Cochin/Tuticorin → Hamburg
            if c2:
                for i in range(8):
                    ship_date = today - timedelta(days=90 * i + random.randint(0, 20))
                    vol = round(random.uniform(20, 50), 2)
                    price = round(random.uniform(5000, 5600), 2)
                    shipments.append(Shipment(
                        tenant_id=tenant_id, company_id=c2.id,
                        source_id=f"TG-HAMBURG-BP-{i+1:04d}",
                        source_provider="tradecrm_internal",
                        shipment_date=ship_date,
                        direction=ShipmentDirection.import_,
                        commodity_text="Black Pepper Malabar Garbled",
                        hs_code="090411",
                        origin_country="India", destination_country="Germany",
                        origin_port_id=cochin.id, destination_port_id=hamburg.id,
                        origin_port_text="Cochin", destination_port_text="Hamburg",
                        volume_mt=vol,
                        unit_price_usd_per_mt=price,
                        value_usd=round(vol * price, 2),
                        trade_partner_name=tenant.company_name,
                        trade_partner_country="India",
                    ))
                for i in range(4):
                    ship_date = today - timedelta(days=90 * i + random.randint(0, 20))
                    vol = round(random.uniform(5, 15), 2)
                    price = round(random.uniform(5200, 5800), 2)
                    shipments.append(Shipment(
                        tenant_id=tenant_id, company_id=c2.id,
                        source_id=f"TG-HAMBURG-BP2-{i+1:04d}",
                        source_provider="tradecrm_internal",
                        shipment_date=ship_date,
                        direction=ShipmentDirection.import_,
                        commodity_text="Black Pepper Tellicherry TGSEB",
                        hs_code="090411",
                        origin_country="India", destination_country="Germany",
                        origin_port_id=tuticorin.id, destination_port_id=hamburg.id,
                        origin_port_text="Tuticorin", destination_port_text="Hamburg",
                        volume_mt=vol,
                        unit_price_usd_per_mt=price,
                        value_usd=round(vol * price, 2),
                        trade_partner_name=tenant.company_name,
                        trade_partner_country="India",
                    ))

            # Savory Foods: 8 Turmeric imports from Tuticorin → Singapore
            if c3:
                for i in range(8):
                    ship_date = today - timedelta(days=180 * (i // 2) + random.randint(0, 30))
                    vol = round(random.uniform(15, 40), 2)
                    price = round(random.uniform(1800, 2400), 2)
                    shipments.append(Shipment(
                        tenant_id=tenant_id, company_id=c3.id,
                        source_id=f"TG-SAVORY-TM-{i+1:04d}",
                        source_provider="tradecrm_internal",
                        shipment_date=ship_date,
                        direction=ShipmentDirection.import_,
                        commodity_text="Black Pepper Whole",
                        hs_code="090411",
                        origin_country="India", destination_country="Singapore",
                        origin_port_id=tuticorin.id, destination_port_id=singapore.id,
                        origin_port_text="Tuticorin", destination_port_text="Singapore PSA",
                        volume_mt=vol,
                        unit_price_usd_per_mt=price,
                        value_usd=round(vol * price, 2),
                        trade_partner_name=tenant.company_name,
                        trade_partner_country="India",
                    ))

            db.add_all(shipments)
            await db.flush()
            print(f"  Created {len(shipments)} mock shipments")

        await db.commit()
        print("\nDone! Mock data seeded successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
