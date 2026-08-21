import { LandingHeader } from "../components/landing/LandingHeader.jsx";
import { Hero } from "../components/landing/Hero.jsx";
import { HowItWorks } from "../components/landing/HowItWorks.jsx";
import { Features } from "../components/landing/Features.jsx";
import { CodeSample } from "../components/landing/CodeSample.jsx";
import { TechStack } from "../components/landing/TechStack.jsx";
import { LandingFooter } from "../components/landing/LandingFooter.jsx";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg">
      <LandingHeader />
      <Hero />
      <HowItWorks />
      <Features />
      <CodeSample />
      <TechStack />
      <LandingFooter />
    </div>
  );
}
