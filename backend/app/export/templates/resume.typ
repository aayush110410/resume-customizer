// ATS-safe, single-column resume. Data arrives as JSON in sys.inputs; strings are inserted as values (never markup).
#let data = json(bytes(sys.inputs.data))
#set page(paper: sys.inputs.at("paper", default: "a4"), margin: (x: 1.7cm, y: 1.5cm))
#set text(font: "Libertinus Serif", size: 10.5pt, lang: "en", hyphenate: false)
#set par(justify: false, leading: 0.55em, spacing: 0.7em)
#set list(indent: 0.4em, body-indent: 0.5em, spacing: 0.45em)

#let section(title) = {
  v(0.5em)
  text(size: 11pt, weight: "bold", tracking: 0.05em, upper(title))
  v(-0.55em)
  line(length: 100%, stroke: 0.5pt + luma(90))
  v(-0.2em)
}
#let bullets(items) = if items.len() > 0 { list(..items.map(b => b.text)) }
#let present(x) = x != none and x != ""
#let entry(e) = {
  let meta = (e.location, if present(e.start) or present(e.end) { (e.start, e.end).filter(present).join(" – ") }).filter(present)
  block(above: 0.7em, below: 0.35em)[
    #text(weight: "bold", e.title)#if present(e.organization) [ — #e.organization]#if meta.len() > 0 [ | #meta.join(" | ")]
  ]
  bullets(e.bullets)
}

#align(center)[
  #text(size: 18pt, weight: "bold", data.contact.name) \
  #(data.contact.email, data.contact.phone, data.contact.location, ..data.contact.links).filter(present).join("  |  ")
]

#if present(data.summary) { section("Summary"); par(data.summary) }
#if data.skills.len() > 0 {
  section("Skills")
  for g in data.skills { par[#text(weight: "bold", g.name): #g.items.join(", ")] }
}
#for (key, title) in (("experience", "Experience"), ("projects", "Projects"), ("education", "Education")) {
  if data.at(key).len() > 0 { section(title); for e in data.at(key) { entry(e) } }
}
#if data.achievements.len() > 0 { section("Achievements"); bullets(data.achievements) }
#for o in data.other_sections { section(o.name); bullets(o.bullets) }
