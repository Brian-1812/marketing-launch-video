# Phase 1 — Understanding the product

The goal of this phase is to be able to say, in one sentence, what job this
product does for whom — and to name the two-to-four screens where it visibly
does it. Everything downstream depends on getting this right, which is why it
ends in a checkpoint with the user.

---

## Given a URL

Use the browser tools (`mcp__claude-in-chrome__*` or Playwright). Load them in
one batch — a browse session needs `navigate`, `read_page`/`get_page_text`,
`computer` for screenshots, and `tabs_create_mcp`.

**1. The landing page tells you their positioning.** Read the hero headline,
the feature sections, the pricing tiers. This is the company telling you what
they think matters. Take it seriously but not literally — landing copy is
aspirational and often lists twelve features when the product has one good
one.

**2. Then find the app.** "Log in", "Try it", "Dashboard", "Open app", a
subdomain like `app.` — the product itself is usually one click from the
landing page and looks completely different.

**3. Extract the design system while you're there.** You'll need it to rebuild
faithfully:

```js
// via javascript_tool / browser_evaluate
const s = getComputedStyle(document.documentElement);
// Dump CSS custom properties — most modern apps put their whole theme here
Array.from(document.styleSheets)
  .flatMap(ss => { try { return Array.from(ss.cssRules) } catch { return [] } })
  .filter(r => r.selectorText === ':root' || r.selectorText === 'html')
  .flatMap(r => Array.from(r.style).map(p => `${p}: ${r.style.getPropertyValue(p)}`))
```

Also capture: the font families actually rendering (`getComputedStyle(el).fontFamily`
on real text, not what the CSS asks for), the border radius scale, the primary
button's exact background, and the shadow definitions. Screenshot each key
screen at 1920×1080 so you can match layout later.

**4. Look for the product's own demo.** Many sites have an animated preview,
a Lottie file, or a `<video>` of the product. If so, watch it — it tells you
which screen the company itself thinks is the money shot.

---

## Given a local repo or dev server

Much better. Read the code.

- Find the theme: `tailwind.config.*`, a `globals.css` with CSS variables, a
  `theme.ts`, a design-tokens file.
- Find the components for the core surface. Copy real `className` strings
  verbatim — a paraphrase is useless, the whole point is fidelity.
- Find the seed/mock data. Products often ship a demo mode or fixtures
  (`VITE_MOCK_API`, `*.fixtures.ts`, a seed script). This is gold: it's
  realistic content the team already approved.
- Find the i18n files if the product is multilingual. Real UI strings beat
  invented ones, and you get other languages free.
- Check git log for recent UI commits. If the product shipped a redesign last
  week, the components you're reading may be newer than any screenshot.

**Ask whether the video project should live inside the repo.** Default to no —
create a sibling directory with its own git repo. Video tooling has heavy
dependencies and a different release cadence than the product. Never modify
the product's source to make the video easier.

---

## Triaging pages

Most products have twenty screens and three that matter. You are looking for
the screen where the product does something a person couldn't easily do
themselves.

**Almost never in the video:** sign-up, log-in, password reset, settings,
account, billing, privacy policy, terms, empty states, 404s, cookie banners,
onboarding tours, changelogs.

**Usually the story:** the main working surface — the editor, the chat, the
canvas, the dashboard, the pipeline view — and whatever artifact it produces.

The test: *if you removed this screen, would the viewer still understand why
the product exists?* If yes, cut it.

A launch video with two screens and a clear story beats one with eight screens
and a tour. Every screen you add costs seconds you don't have.

---

## When the good part is behind auth

Common, and it changes what film you can make. Ask first, then fall back.

**Ask, offering both paths:**

> The core of the product is behind a login, so I can't see the screen the
> video needs to be about. Two options: give me test credentials for a demo
> account, or — if you're running this locally — let me seed a test account
> and some realistic data in your dev environment. Which works?

If they give you credentials:
- Use them only to browse and screenshot. Don't change data, don't send
  messages, don't trigger anything that emails a real person.
- Treat everything you see as confidential. Don't put real customer names,
  real email addresses or real numbers in the video.

If they offer local dev:
- Ask before running seed scripts or migrations. Confirm you're pointed at a
  dev database, not staging or production.
- Prefer any existing demo/mock mode over creating data.

**If neither is available, you can still make a good video** — but a different
one. Say so plainly, then take the path below.

---

## Building from a gated product's landing page

You cannot follow one user through one session, because you can't see the
session. So don't fake it: switch from the single-narrative shape to the
chaptered feature shape (`structure.md`, Shape B). The landing page is
*designed* to enumerate features, which is exactly what that shape needs.

Tell the user what you're doing and why, in one sentence, so the structural
change isn't a surprise at delivery.

### 1. Harvest the feature set

The feature cards are the company's own answer to "what does this do", already
approved and already prioritised by position on the page. Take them at face
value, then cut to three (see `structure.md` for how to order).

```js
// via javascript_tool / browser_evaluate — find the repeated-structure blocks
// that constitute a feature grid, rather than guessing at selectors.
const groups = {};
document.querySelectorAll("section, div[class*=grid], ul").forEach(c => {
  const kids = [...c.children];
  if (kids.length < 2 || kids.length > 8) return;
  const sig = kids.map(k => k.className).join("|");
  if (new Set(kids.map(k => k.className)).size === 1 && kids[0].innerText.trim())
    groups[sig] = kids.map(k => ({
      html: k.outerHTML,
      text: k.innerText.trim(),
      cls: k.className,
      rect: k.getBoundingClientRect(),
    }));
});
groups;
```

For each card capture: the **heading**, the **body copy**, the **icon** (its
SVG path — grab the actual markup, not a description), and the card's computed
styles. That's your chapter labels, already written in the company's voice.

Also worth harvesting: the hero headline and subhead (that's the one-sentence
positioning), any numbers or logos they cite, and the exact CTA wording for the
end slate.

### 2. Reuse the actual components

This is the part people skip, and it's the difference between a video that
looks like the product and a video that looks like a template.

The landing page's own feature cards, badges, buttons, pills, tabs, code
blocks and chrome are **real, shipped, on-brand components that you can see the
markup for**. Vendor them the same way you'd vendor an app component: copy the
real class names, bring the CSS custom properties across, keep the exact radii
and shadows.

Then use them as the film's vocabulary — the chapter card's accent rule, the
end slate's button, the labels on a diagram — so the video and the site look
like one system. When the viewer lands on the site after the video, it should
feel like the same place.

### 3. Reconstruct the interaction each feature describes

A feature card says what happens; your job is to show it. Reconstruct the
screen from whatever evidence exists, in this order of preference:

1. **Product screenshots on the landing page** — often the real UI at full
   fidelity. Read the layout off them directly.
2. **A demo video or animated preview on the site.** If they have one, watch
   it: it's the company showing you the money shot, and you can pull the
   layout, the copy and the flow straight out of it.
3. **Docs and help-centre screenshots.** Usually the most complete source, and
   frequently public even when the app isn't.
4. **A public sandbox, playground, or free tier** that doesn't require the
   gated plan.
5. **App-store or Product Hunt listings**, changelog posts, launch threads.

**Where you have to infer, keep it generic and say so.** A plausible-looking
made-up screen is a real risk here: you may show a button that doesn't exist,
or imply a workflow the product doesn't support. Prefer showing less at higher
confidence — a tight crop on one panel you have evidence for beats a full
screen you invented.

### 4. Say what you inferred

At handover, list every screen that was reconstructed rather than observed, and
offer to redo those beats if they'll share access. Frame it as a question they
can answer in a minute:

> Chapters 2 and 3 are reconstructed from your docs screenshots — I never saw
> the live editor. Worth a look before you post it; if anything's wrong I can
> fix it in an hour, or in ten minutes if you can get me into a demo account.

Nobody minds inference that's declared. Everybody minds finding it themselves.

---

## What to bring to the checkpoint

Show the user, concisely:

1. **What the product does**, in one sentence, in your words. If you've
   misunderstood, this is where it surfaces.
2. **The screens you'll feature**, and the ones you're deliberately skipping.
3. **The hero scenario** — the specific user, the specific request, the
   specific artifact they get. Concrete, not "a user asks a question".
4. **The shot list** with rough timings.
5. **Anything you need from them** — credentials, a logo file, brand hex
   values, a music track, sign-off on the demo content being realistic.

Then build. One checkpoint is enough; don't stop at every phase.
