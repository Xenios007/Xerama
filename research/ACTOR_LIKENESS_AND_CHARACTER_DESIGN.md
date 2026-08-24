# Actor Likeness, Synthetic Casting, and Character Design

_Last researched: 2026-08-24_

## Executive finding

Current AI microdrama production does use real performers as identity/performance anchors in some productions, but the evidence supports a more precise statement than "everyone copies Hollywood actors."

There are at least four different practices:

1. **Licensed digital likeness** — a real actor explicitly permits an AI production to use their face/likeness.
2. **Performance/reference capture** — real actors are used to help generative systems portray expressions and human performance.
3. **Original synthetic characters** — a studio creates a fictional face, locks it as a reusable identity, then carries it through the series using reference images/identity conditioning.
4. **Unlicensed celebrity imitation/deepfake** — technically possible and visible online, but legally and commercially risky. Xerama should not depend on this workflow.

## Verified production examples

### Shortical — *Inevitable*

TheWrap reported in May 2026 that Shortical's AI-generated microdrama *Inevitable* stars an AI version of Israeli actor Aki Avni. Avni was actively involved in the creative process. The story itself concerns a fictional version of the actor licensing his likeness to an AI studio.

This is a useful precedent for Xerama because it demonstrates a legitimate **talent-led digital likeness** model rather than an anonymous synthetic actor.

Source:
- https://www.thewrap.com/media-platforms/tv/shortical-ai-generated-microdrama-aki-avni-inevitable-ofir-lobel/

### Inkitt / Ironblood

Reuters reporting on the 2026 microdrama market states that Ironblood's AI productions use human-written scripts and bring real-life actors into the process to help generative AI portray human expressions. A human director then directs through prompts. The reported production window is roughly three to four weeks for $60,000 or less for an AI production.

Source:
- https://www.reuters.com/business/media-telecom/microdramas-boom-shrinking-hollywood-studios-chase-tiktok-audience-2026-08-18/

## What Xerama should copy from this

The important production technique is not "steal a celebrity face." It is **start from a strong human identity reference and preserve it throughout production**.

For experimentation we can create fictional characters inspired by casting archetypes:

- leading-man facial proportions
- recognizable age range
- wardrobe archetype
- hairstyle
- body build
- screen presence
- expression vocabulary
- cinematography/style references

But the generated character should be a new identity unless Xerama has explicit rights to a real person's likeness.

## Proposed Xerama casting modes

### ORIGINAL_SYNTHETIC
Generate a completely fictional performer and permanently lock the approved root identity.

### LICENSED_LIKENESS
Use photos/scans supplied with documented permission from the performer/rightsholder.

### OWNED_TALENT
Use a performer contracted directly for Xerama productions and maintain explicit usage/replica rights metadata.

### ARCHETYPE_REFERENCE
Use descriptive casting references such as "rugged 40-year-old action lead" rather than naming or reproducing a particular celebrity.

### PROHIBITED / REVIEW REQUIRED
Do not make commercial production depend on an identifiable unlicensed living/deceased celebrity replica.

## Identity asset structure

Each approved synthetic performer should have a permanent identity package:

```text
CHAR_001/
  root_portrait
  neutral_front
  three_quarter_left
  three_quarter_right
  profile_left
  profile_right
  full_body_front
  full_body_side
  expression_sheet
  wardrobe/
  voice/
  identity_metadata.json
```

The root portrait is immutable. New wardrobe/injury/age states derive from that identity rather than regenerating a person from text.

## Current reference-first practice

Runway's official Gen-4 References documentation states that one or multiple reference images can preserve characters across different lighting, locations, and treatments, and recommends clean, evenly lit, neutral reference portraits. It supports up to three references per generation.

Sources:
- https://help.runwayml.com/hc/en-us/articles/40042718905875-Creating-with-Gen-4-Image-References
- https://help.runwayml.com/hc/en-us/articles/41170686463635-Advanced-References-Use-Cases

Independent production workflow reports converge on a similar technique: generate a canonical root portrait, build multi-angle/wardrobe sheets from it, and use those sheets as generation anchors rather than re-describing a face from scratch.

Source:
- https://ogunstudios.com/blog/how-to-make-ai-short-drama

## Rights / legal notes for architecture

This is not legal advice, but rights tracking needs to be part of Xerama's data model from day one.

SAG-AFTRA's TV/Theatrical AI guidance says that when a producer creates a synthetic character whose main facial features are clearly recognizable as a real actor and the actor's name/face is used to prompt the system, consent is required under the applicable agreement.

Source:
- https://www.sagaftra.org/sites/default/files/sa_documents/AI%20TVTH.pdf

California Labor Code §927, effective January 1, 2025, regulates certain contract provisions involving digital replicas and requires reasonably specific intended uses plus representation safeguards for covered agreements.

Source:
- https://leginfo.legislature.ca.gov/faces/codes_displayText.xhtml?article=&chapter=1.&division=2.&lawCode=LAB&part=3.&title=

California also expanded protection for digital replicas of deceased personalities through AB 1836.

Source:
- https://www.gov.ca.gov/2024/09/17/governor-newsom-signs-bills-to-protect-digital-likeness-of-performers/

The Philippines is actively considering multiple digital-likeness/deepfake measures. SBN-1714 is titled the Digital Likeness and Deepfake Regulation Act, and House proposals in 2026 include measures addressing unauthorized use of face, voice, identity, and malicious AI impersonation.

Sources:
- https://senate.gov.ph/legislative-documents/bills/615670
- https://congress.gov.ph/committees/committee/view/E504

## Required Xerama metadata

Each character identity should eventually contain:

```json
{
  "identity_source": "original_synthetic | licensed_likeness | owned_talent | archetype_reference",
  "real_person": false,
  "rights_holder": null,
  "consent_record_id": null,
  "allowed_projects": [],
  "allowed_media": [],
  "expiration": null,
  "voice_rights": null,
  "commercial_use_allowed": true
}
```

This allows us to experiment freely with synthetic identities now without designing a production system that later becomes unusable commercially.

## Xerama decision

For Trial 01, use **original synthetic actors**. We can deliberately design them around successful screen archetypes and attractive casting patterns, but not make them recognizable copies of a specific unlicensed actor.

Later, licensed performers can be added as a first-class casting mode without changing the production pipeline.
