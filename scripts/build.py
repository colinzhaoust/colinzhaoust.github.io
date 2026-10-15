#!/usr/bin/env python3
"""Build the two static research pages from research.json. No dependencies."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1]
papers=json.loads((ROOT/'research.json').read_text())
esc=html.escape

def paper(prefix):return next(p for p in papers if p['title'].startswith(prefix))
def ref(prefix,label):
 p=paper(prefix)
 # A public paper should be one click away. Unreleased work keeps a local entry.
 url=p['url'] or f'all-research.html#{p["id"]}'
 return f'<a href="{esc(url,quote=True)}">{esc(label)}</a>'
def authors(text):return esc(text).replace('Xinran Zhao','<strong>Xinran Zhao</strong>')
def entry(p):
 title=esc(p['title'])
 if p['url']:title=f'<a href="{esc(p["url"],quote=True)}">{title}</a>'
 links=' &nbsp;·&nbsp; '.join(f'<a href="{esc(x["url"],quote=True)}">{esc(x["label"])}</a>' for x in p['links'])
 return f'''<article class="publication" id="{p['id']}">
<h3>{title}</h3>
<p class="authors">{authors(p['authors'])}</p>
<p class="venue">{esc(p['venue'])}</p>
{f'<p class="paper-links">{links}</p>' if links else ''}
</article>'''
def group(category,title):
 entries=sorted((p for p in papers if p['category']==category),key=lambda p:p['year'],reverse=True)
 return f'<section id="{category}" class="paper-section"><h2>{title}</h2>'+''.join(entry(p) for p in entries)+'</section>'
def shell(title,body,active):
 return f'''<!doctype html>
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
<link rel="stylesheet" href="site.css">
</head>
<body>
<a class="skip-link" href="#main">Skip to content</a>
<header class="site-header"><nav class="nav" aria-label="Main navigation">
<a class="wordmark" href="index.html">Xinran Zhao</a>
<div class="nav-links">
<a href="index.html#research" {'aria-current="page"' if active=='research' else ''}>Research</a>
<a href="all-research.html" {'aria-current="page"' if active=='all' else ''}>All Research</a>
<a href="index.html#awards">Awards</a>
<a href="data/CV.pdf">CV</a>
<a href="legacy.html">Legacy</a>
</div></nav></header>
<main id="main">{body}</main>
<footer><a href="mailto:xinranz3@andrew.cmu.edu">xinranz3@andrew.cmu.edu</a><span>Updated October 2026</span>
<p>Layout inspired by <a href="https://rulinshao.github.io/">Rulin Shao</a>; <a href="legacy.html">original homepage</a> based on <a href="https://jonbarron.info/">Jon Barron</a>.</p></footer>
</body></html>\n'''

bio='''<section class="intro" aria-labelledby="name">
<div class="intro-heading"><h1 id="name">Xinran Zhao</h1>
<p class="affiliation">PhD Candidate · Carnegie Mellon University</p></div>
<img class="portrait" src="images/xinran_circle.PNG" width="587" height="572" alt="Xinran Zhao">
<div class="intro-copy">
<p> I am a fourth-year PhD candidate at CMU LTI, advised by <a href="https://www.cs.cmu.edu/~sherryw/">Prof. Sherry Wu</a>. My PhD is supported by the <a href="https://www.amazon.science/news/amazon-launches-68-million-ai-phd-fellowship-program">Amazon AI PhD Fellowship</a>. </p> <p>I spent two wonderful summers (2024 and 2026) at Google DeepMind as a student researcher, working on LLM planning, long-horizon code generation, and continual learning with <a href="https://sites.google.com/view/azadenova">Dr. Azade Nova</a> and <a href="https://haniesedghi.com/">Dr. Hanie Sedghi</a>. </p> <p>I had a great summer 2025 at Ai2 working on deep research agents with <a href="https://www.cs.cornell.edu/~varshakishore/">Varsha</a>, <a href="https://www.cs.cmu.edu/~anaik/">Aakanksha</a>, <a href="https://scholar.google.com/citations?user=MY2W9d4AAAAJ&hl=en">Joseph</a>, <a href="https://scholar.google.com/citations?user=f8aP6RMAAAAJ&hl=en">Jay</a>, and <a href="https://jenahwang.github.io/">Jena</a>. </p> <p>I did my MSCS at Stanford University, where I was fortunate to work with <a href="https://nlp.stanford.edu/~manning/">Prof. Christopher Manning</a>. </p> <p> I did my bachelor's degree at <a href="http://www.ust.hk/">HKUST</a>. At HKUST and during my exchange at Cornell, I was fortunate to work with <a href="https://www.cse.ust.hk/~yqsong/">Prof. Yangqiu Song</a>, <a href="https://scholar.google.com/citations?user=nEsOOx8AAAAJ&hl=en">Prof. Dit-Yan Yeung</a>, and <a href="https://www.cs.cornell.edu/home/cardie/">Prof. Claire Cardie</a>.</p> <p> I always feel lucky to meet great mentors along my journey, including but not limited to, <a href="https://www.shikharmurty.com/">Dr. Shikhar Murty</a>, <a href="https://panda0881.github.io/Hongming_Homepage/">Dr. Hongming Zhang</a>, and <a href="https://esdurmus.github.io/">Dr. Esin Durmus</a>.</p> <p> I love to discuss old and new ideas related to or beyond NLP, ML, and LLMs. Do email me to start a chat. </p>
<p class="social"><a href="mailto:xinranz3@andrew.cmu.edu">Email</a><span>/</span><a href="data/CV.pdf">CV</a><span>/</span><a href="https://scholar.google.com/citations?user=iX71amEAAAAJ&amp;hl=en">Google Scholar</a><span>/</span><a href="https://github.com/colinzhaoust">GitHub</a><span>/</span><a href="https://www.linkedin.com/in/xinran-zhao-51b061180">LinkedIn</a></p>
</div>
</section>
<p class="job-market"><strong>I am currently on the industry job market.</strong> <a href="data/CV.pdf">CV</a> · <a href="mailto:xinranz3@andrew.cmu.edu">Get in touch</a></p>'''

themes=f'''<section id="research" class="research-overview"><h2>Research</h2>
<p class="research-lead">I am interested in meaningful research on natural language processing (NLP) and language model agents. My goal is to build efficient, effective, and faithful systems that work with people on complex real-world tasks. Recently, I focus on information seeking and planning in long-horizon scenarios.</p>
<div class="high-level-interests"><p>Some high-level questions I am thinking about:</p>
<ol>
<li>How can agents learn, maintain memory, and evolve over complex long-horizon tasks?</li>
<li>How can models stay aligned with human motives, goals, and intents, especially under high automation? This includes studying multi-turn behaviors and how multimodal inputs shape model representation spaces.</li>
<li>How can agents proactively help humans seek information, learn, and stay educated amid massive artificial artifacts?</li>
</ol></div>
<div class="direction"><h3>Information Seeking &amp; Human–AI Interaction</h3>
<p>I build retrieval and deep research systems that adapt to people's information needs. This includes combining machine and human information sources, generating intent-aware reports, and helping agents recognize when they need human input.</p>
<p class="representatives">{ref('MoR:','Mixture of Retrievers')} · {ref('Improving Attributed','Intent-aware QA')} · {ref('DR Tulu:','DR Tulu')} · {ref('Knowing When','Escalation')}</p></div>
<div class="direction"><h3>Reasoning, Planning &amp; Coding Agents</h3>
<p>I develop methods for long-horizon planning and code generation, including learning from action sequences, revising planning specifications, editing 3D programs from instructions, and adapting agent harnesses to different tasks.</p>
<p class="representatives">{ref('Improving Large Language','Action Sequence Similarity')} · {ref('ReSHAPE:','ReSHAPE')} · {ref('cAST:','cAST')} · {ref('3DCodeEdit:','3DCodeEdit')} · {ref('Better Harnesses','Harness Adaptation')}</p></div>
<div class="direction"><h3>Persuasion &amp; Human–AI Alignment</h3>
<p>I study how language models interpret and respond to people: what makes arguments persuasive, how models reproduce toxic language, and how planning changes debate. I also explore how interaction can align models with a user's goals.</p>
<p class="representatives">{ref('Leveraging Topic','Argument Persuasion')} · {ref('Probing Toxic','Probing Toxic Content')} · {ref('Strategic Planning','Strategic Debate')} · {ref('Efficient Test-Time','Interactive Adaptation')}</p></div>
</section>'''
selected=['Improving Attributed','MoR:','Improving Large Language','Strategic Planning','Beyond Relevance:','cAST:','ReSHAPE:']
selected_html='<section id="selected" class="paper-section"><div class="section-heading"><h2>Selected Research</h2><a href="all-research.html">All research →</a></div><p class="section-note">Representative published and workshop papers across the research directions above. * Equal contribution.</p>'+''.join(entry(paper(t)) for t in selected)+'</section>'
events='<section id="academic-events" class="events"><h2>Academic Events</h2>'+(ROOT/'scripts/events.html').read_text()+'</section>'
collaborations='<section id="collaborations" class="paper-section"><details class="collaboration-fold"><summary><h2>Large-scale Collaborations</h2></summary><div class="collaboration-papers">'+''.join(entry(p) for p in papers if p['category']=='collaborations')+'</div></details></section>'
awards='<section id="awards" class="awards"><h2>Selected Honors &amp; Awards</h2>'+(ROOT/'scripts/awards.html').read_text()+'</section>'
submissions=group('manuscripts','In Submission')
(ROOT/'index.html').write_text(shell('Xinran Zhao',bio+themes+submissions+selected_html+collaborations+events+awards,'research'))
all_intro='''<div class="page-heading"><h1>All Research</h1><p>Publications, submissions, and collaborations. <a href="index.html#research">Explore by research direction</a>.</p><p class="section-note">* Equal contribution.</p></div>
<nav class="section-nav" aria-label="Publication sections"><a href="#manuscripts">In Submission</a><a href="#peer-reviewed">Peer-reviewed</a><a href="#workshops">Workshops</a><a href="#collaborations">Collaborations</a><a href="#academic-events">Academic Events</a></nav>'''
(ROOT/'all-research.html').write_text(shell('All Research · Xinran Zhao',all_intro+submissions+group('peer-reviewed','Peer-reviewed Publications')+group('workshops','Workshop Papers')+collaborations+events,'all'))
print('Built index.html and all-research.html from',len(papers),'papers')
