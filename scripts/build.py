#!/usr/bin/env python3
"""Build the two static research pages from research.json. No dependencies."""
from pathlib import Path
import html,json,hashlib,re,datetime
from link_targets import normalize_links
ROOT=Path(__file__).resolve().parents[1]
papers=json.loads((ROOT/'research.json').read_text())
css_version=hashlib.sha256((ROOT/'site.css').read_bytes()).hexdigest()[:12]
esc=html.escape
SITE='https://colinzhaoust.github.io/'
DESCRIPTION='Xinran Zhao, PhD candidate at Carnegie Mellon University. Research on language model agents, information seeking, reasoning, planning, and human–AI interaction.'

def paper(prefix):return next(p for p in papers if p['title'].startswith(prefix))
def venue(p, detailed=False):
 text=p['venue']
 if not detailed:
  text=text.removeprefix('Findings of ')
 # Abbreviate conference years only, leaving biography and event dates intact.
 return re.sub(r"\b(ACL|NAACL|EACL|EMNLP|ICLR|ICML|NeurIPS|COLM|CVPR|ICCV|AAAI|LREC|TMLR) (?:20)?(\d{2})\b", r"\1'\2", text)

def authors(text):return esc(text).replace('Xinran Zhao','<strong>Xinran Zhao</strong>')
def entry(p, detailed=False, number=None):
 aliases=''.join(f'<span id="{esc(alias,quote=True)}"></span>' for alias in p.get('aliases',[]))
 title=esc(p['title'])
 if p['url']:title=f'<a href="{esc(p["url"],quote=True)}">{title}</a>'
 number_html=f'<span class="publication-number">{number}.</span> ' if number is not None else ''
 links=' &nbsp;·&nbsp; '.join(f'<a href="{esc(x["url"],quote=True)}">{esc(x["label"])}</a>' for x in p['links'])
 inline_links=' '.join(f'<a href="{esc(x["url"],quote=True)}">[{esc(x["label"])}]</a>' for x in p['links']) if detailed else ''
 return f'''<article class="publication" id="{p['id']}">
{aliases}<h3>{number_html}{title}</h3>
<p class="authors">{authors(p['authors'])}</p>
<p class="venue">{esc(venue(p, detailed=detailed))}{f' <span class="inline-paper-links">{inline_links}</span>' if inline_links else ''}</p>
{f'<p class="paper-links">{links}</p>' if links and not detailed else ''}
</article>'''
def group(category,title):
 entries=sorted((p for p in papers if p['category']==category),key=lambda p:p['year'],reverse=True)
 return f'<section id="{category}" class="paper-section"><h2>{title}</h2>'+''.join(entry(p, detailed=True, number=i) for i,p in enumerate(entries,1))+'</section>'
def shell(title,body,active):
 # The footer date follows the build, so it cannot go stale.
 updated=datetime.date.today().strftime('%B %Y')
 url=SITE+('' if active=='home' else 'all-research.html')
 return normalize_links(f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="author" content="Xinran Zhao">
<meta name="description" content="{DESCRIPTION}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{SITE}images/xinran_circle.PNG">
<meta name="twitter:card" content="summary">
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
<footer><span>Updated {updated}</span>
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
<p class="social"><a href="mailto:xinranz3@andrew.cmu.edu">Email</a><span> / </span><a href="data/CV.pdf">CV</a><span> / </span><a href="https://scholar.google.com/citations?user=iX71amEAAAAJ&amp;hl=en">Google Scholar</a><span> / </span><a href="https://www.semanticscholar.org/author/Xinran-Zhao/1500662261">Semantic Scholar</a><span> / </span><a href="https://github.com/colinzhaoust">GitHub</a><span> / </span><a href="https://www.linkedin.com/in/xinran-zhao-51b061180">LinkedIn</a></p>
</div>
</section>
<p class="job-market"><strong><span aria-hidden="true">👨‍💻</span> I am on the 2026&ndash;27 industry job market, with a flexible graduation date!</strong></p>'''

# Home research block: one thesis line, then a few named works per direction with one line each.
# Each item is (title prefix in research.json, short name, venue label or '', one-line description).
directions=[
 ('Building agents that seek information and deliver it proactively.',[
  ('Knowing When','Knowing When to Stop','','coding agents collect enough evidence that they are blocked, yet a third still exhaust their budget. An escalation tool cuts that from 34.0% to 6.7%.'),
  ('Improving Attributed','Intent-aware Deep Research',"ICLR'26",'deep research reports improve when the model makes explicit the implicit intents behind what to write and what to cite, by 12.3 points for small models.'),
  ('MoR:','MoR',"EMNLP'25",'a zero-shot mixture of sparse, dense, and human retrievers, weighted per query.'),
  ('Revela:','Revela',"ICLR'26 Oral",'trains dense retrievers through language modeling, without annotated query–document pairs.')]),
 ('Building agents that plan, code, and forecast their own outcomes.',[
  ('Improving Large Language','Action Sequence Similarity',"ICLR'25",'exemplars chosen by problem similarity can carry very different plans. Choosing by plan similarity instead improves planning accuracy by 11–40 points with 27% fewer exemplars.'),
  ('3DCodeEdit:','3DCodeEdit','','2,592 instruction-guided edits over 108 Blender programs. The strongest models complete fewer than 60% of structural and style edits.'),
  ('Reading the Tea','Tea Leaves','','can LLMs read the start of a training run and predict how it ends?'),
  ('How Should Planning','ReSHAPE',"BiAlign@NeurIPS'26 Oral","users' requests rule out plans they would accept. Showing concrete plans recovers them better than asking about preferences.")]),
 ('Building agents that debate, persuade, and stay honest about what they know.',[
  ('Strategic Planning','TreeDebater',"ICLR'26",'plans a competitive debate on two trees, one rehearsing attacks and defenses, one tracking the live flow to spend limited time on the points that matter. Human judges rate it 15.6% more persuasive than the prior best system.'),
  ('Planning while Listening','Real-Time Debate','','takes debating to live speech, where the agent must plan while it listens and speaks.'),
  ('Fact-and-Reflection','FaR',"ACL'24",'eliciting known facts first, then reflecting on them, lowers calibration error by 23.5% and lets the model voice concern when it is unsure.')]),
]
def work(prefix,name,label,text):
 p=paper(prefix)
 # A public paper is one click away; unreleased work points to its All Research entry, never OpenReview.
 url=p['url'] or f'all-research.html#{p["id"]}'
 note=f' <span class="reference-venue">({esc(label)})</span>' if label else ''
 return f'<li><a class="work-name" href="{esc(url,quote=True)}">{esc(name)}</a>{note}: {esc(text)}</li>'
themes='<section id="research" class="research-overview"><div class="section-heading"><h2>Research</h2><a href="all-research.html">All research →</a></div>\n<p class="research-lead">I build highly autonomous language model agents that seek information, learn from experience, plan, and collaborate with people. Specifically, I work on:</p>\n'+'\n'.join(f'<div class="direction"><h3>{esc(title)}</h3>\n<ul class="work-list">\n'+'\n'.join(work(*w) for w in works)+'\n</ul></div>' for title,works in directions)+'\n</section>'
miscellaneous='<section id="miscellaneous" class="miscellaneous"><h2>Miscellaneous</h2>'+(ROOT/'scripts/miscellaneous.html').read_text()+'</section>'
events='<section id="academic-events" class="events"><h2>Academic Events</h2>'+(ROOT/'scripts/events.html').read_text()+'</section>'
service='<section id="service" class="service"><h2>Service</h2>'+(ROOT/'scripts/service.html').read_text()+'</section>'
def collaborations(detailed=False):
 entries=[p for p in papers if p['category']=='collaborations']
 return '<section id="collaborations" class="paper-section"><details class="collaboration-fold"><summary><h2>Large-scale Collaborations</h2></summary><div class="collaboration-papers">'+''.join(entry(p,detailed=detailed,number=i if detailed else None) for i,p in enumerate(entries,1))+'</div></details></section>'
awards='<section id="awards" class="awards"><h2>Selected Honors and Awards</h2>'+(ROOT/'scripts/awards.html').read_text()+'</section>'
submissions=group('manuscripts','In Submission')
(ROOT/'index.html').write_text(shell('Xinran Zhao',bio+themes+awards+events+service+miscellaneous,'home'))
all_intro='''<div class="page-heading"><h1>All Research</h1><p>Publications, submissions, and collaborations. <a href="index.html#research">Explore by research direction</a>.</p><p class="section-note">* Equal contribution.</p></div>
<nav class="section-nav" aria-label="Publication sections"><a href="#manuscripts">In Submission</a><a href="#peer-reviewed">Peer-reviewed</a><a href="#workshops">Workshops</a><a href="#collaborations">Collaborations</a><a href="#academic-events">Academic Events</a></nav>'''
(ROOT/'all-research.html').write_text(shell('All Research · Xinran Zhao',all_intro+submissions+group('peer-reviewed','Peer-reviewed Publications')+group('workshops','Workshop Papers')+collaborations(detailed=True)+events+service,'all'))
print('Built index.html and all-research.html from',len(papers),'papers')

legacy=ROOT/'legacy.html'
legacy.write_text(normalize_links(legacy.read_text()))
