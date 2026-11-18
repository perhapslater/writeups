---
title: HTB Writeups
description: Retired-machine investigations with the evidence and reasoning behind the commands.
hide:
  - toc
  - footer
---

<div class="pl-home writeups-home">
<div class="page-width">
<section class="journal-hero"><div class="hero-copy"><h1>HTB <br>Writeups</h1><p class="intro">Follow the evidence, the dead ends, and the decisions behind the commands. Retired-machine investigations from first signal to final privilege.</p><a class="collection-link" href="#machine-library"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M14 3H5v18h14V8l-5-5Z"/><path d="M14 3v5h5M8 12h8m-8 4h5"/></svg> Browse all {{ machine_count }} investigations</a></div><section class="case-previews" data-case-previews aria-label="Investigation previews" aria-roledescription="carousel">
  <header class="case-previews-header">
    <h2>Investigation previews</h2>
    <div class="case-preview-controls" aria-label="Preview navigation" hidden>
      <button type="button" class="case-preview-control case-preview-playback" data-preview-playback aria-label="Pause automatic rotation">Pause</button>
      <button type="button" class="case-preview-control case-preview-arrow" data-preview-prev aria-label="Previous investigation"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m14 6-6 6 6 6"/></svg></button>
      <button type="button" class="case-preview-control case-preview-arrow" data-preview-next aria-label="Next investigation"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 6 6 6-6 6"/></svg></button>
    </div>
  </header>
  <div class="case-preview-progress" aria-hidden="true"><span data-preview-progress></span></div>
  <div class="case-preview-slides">{{ investigation_previews }}
  </div>
  <div class="case-preview-pagination" role="group" aria-label="Choose investigation preview" hidden>{{ preview_buttons }}
  </div>
  <p class="sr-only" data-preview-status role="status"></p>
</section>
</section><section class="library" id="machine-library" aria-labelledby="library-title"><div class="library-title"><h2 id="library-title">Machine library</h2><p>Every path has something to teach.</p></div><div class="library-filters"><div class="library-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10.8" cy="10.8" r="6.5"/><path d="m16 16 4.5 4.5"/></svg><label class="sr-only" for="machine-search">Search machines or techniques</label><input id="machine-search" type="search" placeholder="Search machines or techniques" value="" autocomplete="off"></div><div class="filter-field"><label for="platform-filter">Platform</label><select id="platform-filter"><option selected>All platforms</option><option >Active Directory</option><option >Windows</option><option >Linux</option></select></div><div class="filter-field"><label for="difficulty-filter">Difficulty</label><select id="difficulty-filter"><option selected>Any difficulty</option>{{ difficulty_options }}</select></div></div><div class="results-line"><span id="machine-count" role="status" aria-live="polite"></span><button class="clear-filters" id="clear-filters" type="button">Reset filters</button></div><div class="machine-grid" id="machine-grid">{{ machine_cards }}</div></section>
</div>
</div>
