#!/usr/bin/env python3
"""Build the two static research pages from research.json. No dependencies."""
from pathlib import Path
import html,json,hashlib,re
from link_targets import normalize_links
ROOT=Path(__file__).resolve().parents[1]
papers=json.loads((ROOT/'research.json').read_text())
css_version=hashlib.sha256((ROOT/'site.css').read_bytes()).hexdigest()[:12]
esc=html.escape

def paper(prefix):return next(p for p in papers if p['title'].startswith(prefix))
def venue(p, detailed=False):
 text=p['venue']
 if not detailed:
  text=text.removeprefix('Findings of ')
 # Abbreviate conference years only, leaving biography and event dates intact.
 return re.sub(r"\b(ACL|NAACL|EACL|EMNLP|ICLR|ICML|NeurIPS|COLM|CVPR|ICCV|AAAI|LREC|TMLR) (?:20)?(\d{2})\b", r"\1'\2", text)

def ref(prefix,label,topic=None):
 p=paper(prefix)
 # A public paper should be one click away. Unreleased work keeps a local entry.
 url=p['url'] or f'all-research.html#{p["id"]}'
 # Overview labels keep the primary venue; distinctions remain in full entries.
 conference=venue(p).split(' · ')[0]
 if topic and conference == 'In submission':
  conference='in submission'
 annotation=f'{topic}, {conference}' if topic else conference
 return f'<span class="research-reference"><a href="{esc(url,quote=True)}">{esc(label)}</a> <span class="reference-venue">({esc(annotation)})</span></span>'
def refs(items):
 return ' · '.join(ref(*item) for item in sorted(items,key=lambda item:paper(item[0])['year'],reverse=True))
def authors(text):return esc(text).replace('Xinran Zhao','<strong>Xinran Zhao</strong>')
def entry(p, detailed=False, number=None, compact_links=False):
 aliases=''.join(f'<span id="{esc(alias,quote=True)}"></span>' for alias in p.get('aliases',[]))
 title=esc(p['title'])
 if p['url']:title=f'<a href="{esc(p["url"],quote=True)}">{title}</a>'
 number_html=f'<span class="publication-number">{number}.</span> ' if number is not None else ''
 links=' &nbsp;·&nbsp; '.join(f'<a href="{esc(x["url"],quote=True)}">{esc(x["label"])}</a>' for x in p['links'])
 inline_links=' '.join(f'<a href="{esc(x["url"],quote=True)}">[{esc(x["label"])}]</a>' for x in p['links']) if detailed or compact_links else ''
 return f'''<article class="publication" id="{p['id']}">
{aliases}<h3>{number_html}{title}</h3>
<p class="authors">{authors(p['authors'])}</p>
<p class="venue">{esc(venue(p, detailed=detailed))}{f' <span class="inline-paper-links">{inline_links}</span>' if inline_links else ''}</p>
{f'<p class="paper-links">{links}</p>' if links and not (detailed or compact_links) else ''}
</article>'''
def group(category,title):
 entries=sorted((p for p in papers if p['category']==category),key=lambda p:p['year'],reverse=True)
 return f'<section id="{category}" class="paper-section"><h2>{title}</h2>'+''.join(entry(p, detailed=True, number=i) for i,p in enumerate(entries,1))+'</section>'
def shell(title,body,active):
 return normalize_links(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="Xinran Zhao">
<meta name="description" content="Xinran Zhao, PhD candidate at Carnegie Mellon University. Research on language model agents, information seeking, reasoning, planning, and human–AI interaction.">
<meta name="google-site-verification" content="LwD5w9ZnQlSTsmKcIz8OKY0fQtgaaxa_QGAhDlwJ6eI">
<title>{esc(title)}</title>
<link rel="icon" type="image/png" href="images/lti.png">
<link rel="stylesheet" href="fonts.css">
<link rel="stylesheet" href="site.css?v={css_version}">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><nav class="nav" aria-label="Main navigation">
<a class="wordmark" href="index.html">Xinran Zhao</a>
<div class="nav-links">
<a href="index.html" {'aria-current="page"' if active=='home' else ''}>Home</a>
<a href="all-research.html" {'aria-current="page"' if active=='all' else ''}>All Research</a>
<a href="index.html#awards">Awards</a>
<a href="data/CV.pdf">CV</a>
<a href="legacy.html">Legacy</a>
</div></nav></header>
<main id="main">{body}</main>
<footer><span>Updated October 2026</span>
<p>Layout inspired by <a href="https://jonbarron.info/">Jon Barron</a>.</p></footer>
</body></html>\n''')

bio='''<section class="intro" aria-labelledby="name">
<div class="intro-heading"><h1 id="name">Xinran Zhao</h1>
<p class="affiliation">PhD Candidate · Carnegie Mellon University</p></div>
<img class="portrait" src="images/xinran_circle.PNG" width="587" height="572" alt="Xinran Zhao">
<div class="intro-copy">
<p>I am a fourth-year PhD candidate at CMU LTI, advised by <a href="https://www.cs.cmu.edu/~sherryw/">Sherry Wu</a>. My PhD is supported by the <a href="https://www.amazon.science/news/amazon-launches-68-million-ai-phd-fellowship-program">Amazon AI PhD Fellowship</a>.</p>
<p>At Google DeepMind (2024, 2026), I worked as a student researcher on LLM planning, long-horizon code generation, and continual learning with <a href="https://sites.google.com/view/azadenova">Azade Nova</a> and <a href="https://haniesedghi.com/">Hanie Sedghi</a>.&ensp;At Ai2 (2025), I worked on deep research agents with <a href="https://www.cs.cornell.edu/~varshakishore/">Varsha</a>, <a href="https://www.cs.cmu.edu/~anaik/">Aakanksha</a>, <a href="https://scholar.google.com/citations?user=MY2W9d4AAAAJ&hl=en">Joseph</a>, <a href="https://scholar.google.com/citations?user=f8aP6RMAAAAJ&hl=en">Jay</a>, and <a href="https://jenahwang.github.io/">Jena</a>.</p>
<p>I received my MSCS from Stanford, where I worked with <a href="https://nlp.stanford.edu/~manning/">Christopher Manning</a>, and my bachelor's degree from <a href="http://www.ust.hk/">HKUST</a>. At HKUST and during my exchange at Cornell, I was fortunate to work with <a href="https://www.cse.ust.hk/~yqsong/">Yangqiu Song</a>, <a href="https://scholar.google.com/citations?user=nEsOOx8AAAAJ&hl=en">Dit-Yan Yeung</a>, and <a href="https://www.cs.cornell.edu/home/cardie/">Claire Cardie</a>.</p>
<p>I always feel lucky to meet great mentors along my journey, including but not limited to, <a href="https://www.shikharmurty.com/">Shikhar Murty</a>, <a href="https://panda0881.github.io/Hongming_Homepage/">Hongming Zhang</a>, and <a href="https://esdurmus.github.io/">Esin Durmus</a>.</p>
<p class="social"><a href="mailto:xinranz3@andrew.cmu.edu">Email</a><span> / </span><a href="data/CV.pdf">CV</a><span> / </span><a href="https://scholar.google.com/citations?user=iX71amEAAAAJ&amp;hl=en">Google Scholar</a><span> / </span><a href="https://github.com/colinzhaoust">GitHub</a><span> / </span><a href="https://www.linkedin.com/in/xinran-zhao-51b061180">LinkedIn</a></p>
</div>
</section>
<p class="job-market"><strong><span aria-hidden="true">👨‍💻</span> I am currently on the industry job market!</strong></p>'''

themes=f'''<section id="research" class="research-overview"><h2>Research</h2>
<p class="research-lead">I am interested in meaningful research on natural language processing (NLP) and language model agents. My goal is to build efficient, effective, and faithful systems that work with people on complex real-world tasks. Recently, I focus on information seeking and planning in long-horizon scenarios.</p>
<div class="high-level-interests"><p>Some high-level questions I am thinking about:</p>
<ol>
<li>How can agents learn, maintain memory, and evolve over complex long-horizon tasks?</li>
<li>How can models stay aligned with human motives, goals, and intents, especially under high automation? This includes studying multi-turn behaviors and how multimodal inputs shape model representation spaces.</li>
<li>How can agents proactively help humans seek information, learn, and stay educated amid massive artificial artifacts?</li>
</ol></div>
<div class="direction"><h3>Information Seeking &amp; Delivery</h3>
<p class="representatives">{refs([('Knowing When','Escalation','proactive delivery'),('DR Tulu:','DR Tulu'),('Improving Attributed','Intent-aware QA'),('Revela:','Revela'),('MoR:','Mixture of Retrievers'),('Beyond Relevance:','PIR'),('Dense X Retrieval:','Dense X'),('MixGR:','MixGR'),('Thrust:','Thrust','when to retrieve')])}</p></div>
<div class="direction"><h3>Reasoning, Planning, Forecasting &amp; Coding Agents</h3>
<p class="representatives">{refs([('3DCodeEdit:','3D Code Editing'),('Reading the Tea','Tea Leaves'),('How Should Planning','ReSHAPE'),('Better Harnesses','Harness Adaptation'),('Pivot-ICL:','Pivot-ICL'),("The Ramon Llull's",'Ramon Llull'),('cAST:','cAST'),('Improving Large Language','Action Sequence Similarity')])}</p></div>
<div class="direction"><h3>Persuasion &amp; Human–AI Alignment</h3>
<p class="representatives">{refs([('Planning while Listening','Real-Time Debate'),('Strategic Planning','Strategic Debate'),('SPHERE:','SPHERE'),('Fact-and-Reflection','FaR','LLM honesty'),('Leveraging Topic','Argument Persuasion'),('Probing Toxic','Probing Toxic Content')])}</p></div>
</section>'''
# Include the user's selected manuscripts alongside published representative work.
# Sort by year; within a year, retain the explicit editorial order below.
selected=['3DCodeEdit:','Planning while Listening','How Should Planning','Reading the Tea','Knowing When to Stop:','Better Harnesses,','Improving Attributed','Strategic Planning',"The Ramon Llull's",'MoR:','cAST:','Improving Large Language','Beyond Relevance:','Fact-and-Reflection','Thrust:']
selected=sorted(selected,key=lambda title:paper(title)['year'],reverse=True)
selected_html='<section id="selected" class="paper-section"><div class="section-heading"><h2>Selected Research</h2><a href="all-research.html">All research →</a></div><p class="section-note">Selected publications and ongoing work. * Equal contribution.</p>'+''.join(entry(paper(t),number=i,compact_links=True) for i,t in enumerate(selected,1))+'</section>'
miscellaneous='<section id="miscellaneous" class="miscellaneous"><h2>Miscellaneous</h2>'+(ROOT/'scripts/miscellaneous.html').read_text()+'</section>'
events='<section id="academic-events" class="events"><h2>Academic Events</h2>'+(ROOT/'scripts/events.html').read_text()+'</section>'
def collaborations(detailed=False):
 entries=[p for p in papers if p['category']=='collaborations']
 return '<section id="collaborations" class="paper-section"><details class="collaboration-fold"><summary><h2>Large-scale Collaborations</h2></summary><div class="collaboration-papers">'+''.join(entry(p,detailed=detailed,number=i if detailed else None) for i,p in enumerate(entries,1))+'</div></details></section>'
awards='<section id="awards" class="awards"><h2>Selected Honors and Awards</h2>'+(ROOT/'scripts/awards.html').read_text()+'</section>'
submissions=group('manuscripts','In Submission')
(ROOT/'index.html').write_text(shell('Xinran Zhao',bio+themes+awards+selected_html+collaborations()+events+miscellaneous,'home'))
all_intro='''<div class="page-heading"><h1>All Research</h1><p>Publications, submissions, and collaborations. <a href="index.html#research">Explore by research direction</a>.</p><p class="section-note">* Equal contribution.</p></div>
<nav class="section-nav" aria-label="Publication sections"><a href="#manuscripts">In Submission</a><a href="#peer-reviewed">Peer-reviewed</a><a href="#workshops">Workshops</a><a href="#collaborations">Collaborations</a><a href="#academic-events">Academic Events</a></nav>'''
(ROOT/'all-research.html').write_text(shell('All Research · Xinran Zhao',all_intro+submissions+group('peer-reviewed','Peer-reviewed Publications')+group('workshops','Workshop Papers')+collaborations(detailed=True)+events,'all'))
print('Built index.html and all-research.html from',len(papers),'papers')

legacy=ROOT/'legacy.html'
legacy.write_text(normalize_links(legacy.read_text()))
