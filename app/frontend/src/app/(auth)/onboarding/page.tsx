"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
// import { useAuth } from "@clerk/nextjs"; // disabled for dev mode
import { Button } from "@/components/ui/Button";
import { Input, Textarea } from "@/components/ui/Input";
import { Rocket, ArrowRight, ArrowLeft, Check } from "@phosphor-icons/react";
import { api, getErrorMessage } from "@/lib/api";

const COMMODITY_OPTIONS = [
  "Pepper", "Coffee", "Cloves", "Cardamom", "Turmeric",
  "Seafood", "Rice", "Tea", "Spices", "Cashew", "Coconut", "Other",
];

const MARKET_OPTIONS = [
  "USA", "Germany", "UAE", "UK", "Netherlands", "Saudi Arabia",
  "Japan", "China", "Vietnam", "Brazil", "Turkey", "Other",
];

export default function OnboardingPage() {
  const router = useRouter();
  // const { getToken } = useAuth(); // disabled for dev mode
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);

  const [companyName, setCompanyName] = useState("");
  const [about, setAbout] = useState("");
  const [selectedCommodities, setSelectedCommodities] = useState<string[]>([]);
  const [selectedMarkets, setSelectedMarkets] = useState<string[]>([]);

  // Wire token on mount
  // api.setTokenProvider(async () => await getToken()); // disabled for dev mode

  const toggleItem = (item: string, list: string[], setList: (v: string[]) => void) => {
    setList(list.includes(item) ? list.filter((i) => i !== item) : [...list, item]);
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      await api.put("/tenants/settings", {
        company_name: companyName || undefined,
        about: about || undefined,
        commodities: selectedCommodities,
        target_markets: selectedMarkets,
      });
    } catch {
      // Settings save failed — still redirect, user can update later
    }
    router.push("/dashboard");
  };

  if (step === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-[560px]">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold font-[family-name:var(--font-heading)] text-primary mb-1">
              Welcome to Tradyon Outreach
            </h1>
            <p className="text-sm text-text-secondary">
              Let us set up your workspace in a few steps
            </p>
          </div>
          <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-8 shadow-[var(--shadow-md)]">
            <div className="flex flex-col items-center text-center py-8">
              <Rocket className="h-16 w-16 text-primary mb-4" />
              <h2 className="text-lg font-semibold font-[family-name:var(--font-heading)] mb-2">
                Set up your workspace
              </h2>
              <p className="text-sm text-text-secondary max-w-sm mb-6">
                Tell us about your export business so we can personalize your outreach experience.
              </p>
              <Button onClick={() => setStep(1)}>
                Get Started <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === 1) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-[560px]">
          <div className="text-center mb-6">
            <p className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Step 1 of 3</p>
            <h1 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
              Company Profile
            </h1>
          </div>
          <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-6 shadow-[var(--shadow-md)] space-y-4">
            <Input
              label="Company Name"
              placeholder="Your export company name"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
            />
            <Textarea
              label="About your company"
              placeholder="Brief description of your business, products, and expertise..."
              value={about}
              onChange={(e) => setAbout(e.target.value)}
            />
            <div className="flex justify-between pt-2">
              <Button variant="ghost" onClick={() => setStep(0)}>
                <ArrowLeft className="h-4 w-4 mr-1" /> Back
              </Button>
              <Button onClick={() => setStep(2)}>
                Next <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (step === 2) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background px-4">
        <div className="w-full max-w-[560px]">
          <div className="text-center mb-6">
            <p className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Step 2 of 3</p>
            <h1 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
              What do you export?
            </h1>
          </div>
          <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-6 shadow-[var(--shadow-md)]">
            <p className="text-sm text-text-secondary mb-3">Select your commodities</p>
            <div className="flex flex-wrap gap-2 mb-6">
              {COMMODITY_OPTIONS.map((c) => (
                <button
                  key={c}
                  onClick={() => toggleItem(c, selectedCommodities, setSelectedCommodities)}
                  className={`px-3 py-1.5 rounded-[var(--radius-full)] text-sm border transition-colors cursor-pointer ${
                    selectedCommodities.includes(c)
                      ? "bg-primary text-text-inverse border-primary"
                      : "bg-surface text-text-secondary border-border hover:border-primary-lighter"
                  }`}
                >
                  {selectedCommodities.includes(c) && <Check className="h-3 w-3 inline mr-1" weight="bold" />}
                  {c}
                </button>
              ))}
            </div>
            <div className="flex justify-between pt-2">
              <Button variant="ghost" onClick={() => setStep(1)}>
                <ArrowLeft className="h-4 w-4 mr-1" /> Back
              </Button>
              <Button onClick={() => setStep(3)}>
                Next <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Step 3: Markets
  return (
    <div className="min-h-screen flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-[560px]">
        <div className="text-center mb-6">
          <p className="text-xs text-text-tertiary uppercase tracking-wide mb-1">Step 3 of 3</p>
          <h1 className="text-xl font-bold font-[family-name:var(--font-heading)] text-text-primary">
            Target Markets
          </h1>
        </div>
        <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-6 shadow-[var(--shadow-md)]">
          <p className="text-sm text-text-secondary mb-3">Where do you want to find buyers?</p>
          <div className="flex flex-wrap gap-2 mb-6">
            {MARKET_OPTIONS.map((m) => (
              <button
                key={m}
                onClick={() => toggleItem(m, selectedMarkets, setSelectedMarkets)}
                className={`px-3 py-1.5 rounded-[var(--radius-full)] text-sm border transition-colors cursor-pointer ${
                  selectedMarkets.includes(m)
                    ? "bg-primary text-text-inverse border-primary"
                    : "bg-surface text-text-secondary border-border hover:border-primary-lighter"
                }`}
              >
                {selectedMarkets.includes(m) && <Check className="h-3 w-3 inline mr-1" weight="bold" />}
                {m}
              </button>
            ))}
          </div>
          <div className="flex justify-between pt-2">
            <Button variant="ghost" onClick={() => setStep(2)}>
              <ArrowLeft className="h-4 w-4 mr-1" /> Back
            </Button>
            <Button onClick={handleFinish} isLoading={loading}>
              Finish Setup <Check className="h-4 w-4 ml-1" weight="bold" />
            </Button>
          </div>

          <button
            onClick={() => router.push("/dashboard")}
            className="w-full mt-4 text-xs text-text-tertiary hover:text-text-secondary transition-colors cursor-pointer"
          >
            Skip for now
          </button>
        </div>
      </div>
    </div>
  );
}
