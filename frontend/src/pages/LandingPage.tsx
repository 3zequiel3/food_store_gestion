import { LandingHeader } from './landing/sections/LandingHeader';
import { HeroSection } from './landing/sections/HeroSection';
import { StatsBarSection } from './landing/sections/StatsBarSection';
import { CategoriesSection } from './landing/sections/CategoriesSection';
import { FeaturedProductsSection } from './landing/sections/FeaturedProductsSection';
import { HowItWorksSection } from './landing/sections/HowItWorksSection';
import { FooterSection } from './landing/sections/FooterSection';

/** Landing page composer. Each section lives in its own file under landing/sections/. */
export function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <LandingHeader />
      <main>
        <HeroSection />
        <StatsBarSection />
        <CategoriesSection />
        <FeaturedProductsSection />
        <HowItWorksSection />
      </main>
      <FooterSection />
    </div>
  );
}
