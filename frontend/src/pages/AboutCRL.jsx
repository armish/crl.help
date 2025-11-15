/**
 * About CRL Page
 *
 * Displays comprehensive information about FDA Complete Response Letters
 * with a sticky sidebar navigation for easy section access.
 */

import { useState, useEffect } from 'react';

export default function AboutCRL() {
  const [activeSection, setActiveSection] = useState('what-is-crl');

  // Table of contents structure matching the CRL.md sections
  const sections = [
    { id: 'what-is-crl', title: 'What Is a Complete Response Letter?' },
    { id: 'what-to-expect', title: 'What to Expect in a CRL' },
    { id: 'types-of-applications', title: 'Types of Applications' },
    { id: 'action-letters', title: 'Types of Action Letters' },
    { id: 'common-reasons', title: 'Why Does FDA Issue CRLs?' },
    { id: 'therapy-types', title: 'Types of Therapies' },
    { id: 'why-matter', title: 'Why Do CRLs Matter?' },
  ];

  // Auto-update active section based on scroll position
  useEffect(() => {
    const handleScroll = () => {
      const sectionElements = sections.map(s => document.getElementById(s.id));
      const scrollPosition = window.scrollY + 100;

      for (let i = sectionElements.length - 1; i >= 0; i--) {
        const element = sectionElements[i];
        if (element && element.offsetTop <= scrollPosition) {
          setActiveSection(sections[i].id);
          break;
        }
      }
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const scrollToSection = (sectionId) => {
    const element = document.getElementById(sectionId);
    if (element) {
      const yOffset = -80; // Account for fixed header
      const y = element.getBoundingClientRect().top + window.pageYOffset + yOffset;
      window.scrollTo({ top: y, behavior: 'smooth' });
    }
  };

  return (
    <div className="flex gap-8">
      {/* Sidebar Navigation */}
      <aside className="hidden lg:block w-64 flex-shrink-0">
        <div className="sticky top-24">
          <h2 className="text-sm font-semibold text-gray-900 mb-4">On This Page</h2>
          <nav className="space-y-1">
            {sections.map((section) => (
              <button
                key={section.id}
                onClick={() => scrollToSection(section.id)}
                className={`block w-full text-left px-3 py-2 text-sm rounded-md transition-colors ${
                  activeSection === section.id
                    ? 'bg-blue-50 text-blue-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                {section.title}
              </button>
            ))}
          </nav>
        </div>
      </aside>

      {/* Main Content */}
      <article className="flex-1 max-w-3xl prose prose-blue prose-lg">
        {/* Header */}
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          Understanding FDA Complete Response Letters (CRLs)
        </h1>
        <p className="text-lg text-gray-600 italic mb-8">
          A simple guide for scientists, clinicians, and anyone curious about how FDA reviews new medicines.
        </p>

        <hr className="my-8" />

        {/* Section 1: What Is a CRL? */}
        <section id="what-is-crl" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">What Is a Complete Response Letter?</h2>

          <p className="mb-4">
            A <strong>Complete Response Letter (CRL)</strong> is an official notice from the U.S. Food and Drug Administration (FDA) telling a company:
          </p>

          <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-700 my-6">
            "We finished our review of your drug application, but we can't approve it in its current form."
          </blockquote>

          <p className="mb-4">
            A CRL <strong>is not a rejection</strong>.
            It's more like receiving a detailed "to-do list" explaining what the company needs to fix—whether in its data, manufacturing, labeling, or clinical studies—before approval can happen.
          </p>

          <p>
            In 2025, the FDA announced a new transparency initiative to <strong>publish many CRLs publicly</strong>. This lets researchers, patients, and clinicians better understand why certain drugs are not approved in their first review cycle.
          </p>
        </section>

        <hr className="my-8" />

        {/* Section 2: What to Expect */}
        <section id="what-to-expect" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">What Should You Expect to See in a CRL?</h2>

          <p className="mb-4">A typical CRL includes:</p>

          <h3 className="text-2xl font-semibold text-gray-900 mt-6 mb-3">1. What FDA reviewed</h3>
          <ul className="list-disc pl-6 mb-4">
            <li>Clinical trials</li>
            <li>Manufacturing/quality data</li>
            <li>Safety monitoring</li>
            <li>Product labeling</li>
            <li>Facility inspections</li>
          </ul>

          <h3 className="text-2xl font-semibold text-gray-900 mt-6 mb-3">2. The specific problems preventing approval</h3>
          <p className="mb-2">For example:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>A trial didn't convincingly show the drug works.</li>
            <li>The manufacturing site didn't pass inspection.</li>
            <li>Lab tests used to measure potency weren't validated.</li>
            <li>A drug-device combination (like an injector) didn't perform reliably.</li>
          </ul>

          <h3 className="text-2xl font-semibold text-gray-900 mt-6 mb-3">3. What the company must do next</h3>
          <p className="mb-2">This could include:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Running another study</li>
            <li>Fixing a manufacturing process</li>
            <li>Updating the drug label</li>
            <li>Providing more stability or toxicology data</li>
            <li>Correcting issues at a drug-production facility</li>
          </ul>

          <p className="mt-4">
            FDA does <strong>not</strong> tell a company how to fix the issues—only what the deficiencies are.
            A company can then resubmit the application once it has addressed them.
          </p>
        </section>

        <hr className="my-8" />

        {/* Section 3: Types of Applications */}
        <section id="types-of-applications" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Types of Applications That Can Receive CRLs</h2>

          <p className="mb-4">When companies ask FDA to approve a new medicine, they submit an application. The two main types are:</p>

          <h3 className="text-2xl font-semibold text-gray-900 mt-6 mb-3">NDA — New Drug Application</h3>
          <p className="mb-2">Used for:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Traditional small-molecule drugs</li>
            <li>Some peptides</li>
            <li>505(b)(2) applications that rely partly on published literature or an already-approved drug</li>
          </ul>

          <h3 className="text-2xl font-semibold text-gray-900 mt-6 mb-3">BLA — Biologics License Application</h3>
          <p className="mb-2">Used for:</p>
          <ul className="list-disc pl-6 mb-4">
            <li>Biologics (antibodies, proteins)</li>
            <li>Biosimilars</li>
            <li>Cell and gene therapies</li>
            <li>Vaccines</li>
          </ul>

          <p className="mt-4">
            When FDA issues a CRL, it will specify whether it applies to an NDA or BLA.
          </p>
        </section>

        <hr className="my-8" />

        {/* Section 4: Types of Action Letters */}
        <section id="action-letters" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Types of FDA "Action Letters" (including CRLs)</h2>

          <p className="mb-4">FDA uses several kinds of regulatory letters during drug review:</p>

          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">Complete Response (CRL)</h3>
              <p className="text-gray-700">FDA finished the review but cannot approve the product in its current form.</p>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Approval Letter</h3>
              <p className="text-gray-700">The drug is approved for marketing.</p>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Tentative Approval</h3>
              <p className="text-gray-700">
                The drug meets scientific/quality requirements but <strong>cannot</strong> be approved yet due to patent/exclusivity barriers.
                Common for generics and 505(b)(2) drugs.
              </p>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Refusal to File (RTF)</h3>
              <p className="text-gray-700">
                The application was missing major components.
                FDA stops the review before it even starts.
              </p>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Other Administrative Letters</h3>
              <p className="text-gray-700">
                Such as "Provisional Determination" or "Rescinded CRL"—these are less common and are usually procedural.
              </p>
            </div>
          </div>
        </section>

        <hr className="my-8" />

        {/* Section 5: Common Reasons for CRLs */}
        <section id="common-reasons" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Why Does FDA Issue CRLs? (Most Common Reasons)</h2>

          <p className="mb-6">
            CRL reasons tend to fall into a few big buckets.
            These are based on analysis of &gt;350 CRLs released under FDA's transparency initiative.
          </p>

          <div className="space-y-6">
            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">1. Clinical Issues</h3>
              <ul className="list-disc pl-6">
                <li>Trial didn't show effectiveness</li>
                <li>Safety database too small</li>
                <li>PK or bioequivalence mismatch</li>
                <li>Poor trial conduct or missing data</li>
              </ul>
            </div>

            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">2. CMC / Quality Issues</h3>
              <p className="text-sm text-gray-600 mb-2">(CMC = Chemistry, Manufacturing, and Controls)</p>
              <ul className="list-disc pl-6">
                <li>Impurities above limits</li>
                <li>Unstable formulation</li>
                <li>Failed potency or identity tests</li>
                <li>Inadequate analytical methods</li>
              </ul>
            </div>

            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">3. Facilities / CGMP Issues</h3>
              <p className="text-sm text-gray-600 mb-2">(CGMP = current Good Manufacturing Practices)</p>
              <ul className="list-disc pl-6">
                <li>Manufacturing site failed inspection</li>
                <li>Sterility concerns</li>
                <li>Batch records incomplete</li>
                <li>FDA couldn't perform a required inspection</li>
              </ul>
            </div>

            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">4. Device / Combination Product Issues</h3>
              <p className="text-sm text-gray-600 mb-2">For products with injectors, pumps, on-body devices, etc.</p>
              <ul className="list-disc pl-6">
                <li>Human factors problems</li>
                <li>Reliability failures (e.g., pump underruns)</li>
                <li>Design verification not complete</li>
              </ul>
            </div>

            <div>
              <h3 className="text-2xl font-semibold text-gray-900 mb-3">5. Regulatory / Labeling / Other</h3>
              <ul className="list-disc pl-6">
                <li>Missing REMS (risk management program)</li>
                <li>Inaccurate or incomplete label</li>
                <li>Administrative gaps or missing modules</li>
              </ul>
            </div>
          </div>
        </section>

        <hr className="my-8" />

        {/* Section 6: Therapy Types */}
        <section id="therapy-types" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">What Types of Therapies Often Appear in CRLs?</h2>

          <p className="mb-6">CRLs occur across all therapeutic categories, but certain areas show patterns:</p>

          <div className="space-y-4">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">High rates of CMC/facility issues</h3>
              <ul className="list-disc pl-6">
                <li>Sterile injectables</li>
                <li>Biologics</li>
                <li>Gene therapies</li>
              </ul>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Higher rates of clinical issues</h3>
              <ul className="list-disc pl-6">
                <li>Neurology & psychiatry (trial endpoints harder to interpret)</li>
                <li>Rare disease indications (small trials, limited datasets)</li>
                <li>505(b)(2) products trying to bridge to older data</li>
              </ul>
            </div>

            <div>
              <h3 className="text-xl font-semibold text-gray-900">Higher device/human factors issues</h3>
              <ul className="list-disc pl-6">
                <li>Diabetes (pumps, injectors)</li>
                <li>Dermatology (autoinjectors, on-body patches)</li>
                <li>Pain management devices</li>
              </ul>
            </div>
          </div>
        </section>

        <hr className="my-8" />

        {/* Section 7: Why CRLs Matter */}
        <section id="why-matter" className="mb-12">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Why Do CRLs Matter?</h2>

          <p className="mb-4">CRLs affect:</p>
          <ul className="list-disc pl-6 mb-6">
            <li><strong>Patients</strong>, by delaying access to treatments</li>
            <li><strong>Companies</strong>, by pushing back launch timelines</li>
            <li><strong>Clinicians</strong>, who depend on up-to-date information</li>
            <li><strong>Researchers</strong>, by highlighting methodological issues that can guide better study design</li>
            <li><strong>Investors</strong>, due to financial and competitive implications</li>
          </ul>

          <p>With FDA now publishing many CRLs publicly, the scientific community can learn:</p>
          <ul className="list-disc pl-6">
            <li>What types of problems most often derail approvals</li>
            <li>How companies can improve study design and manufacturing quality</li>
            <li>Where regulatory science is evolving</li>
          </ul>
        </section>
      </article>
    </div>
  );
}
