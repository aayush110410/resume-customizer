#let data = json(bytes(sys.inputs.data))
#set page(paper: sys.inputs.at("paper", default: "a4"), margin: (x: 2.4cm, y: 2.2cm))
#set text(font: "Libertinus Serif", size: 11pt, lang: "en", hyphenate: false)
#set par(justify: false, leading: 0.65em, spacing: 1.35em)
#let present(x) = x != none and x != ""

#text(size: 18pt, weight: "bold", data.contact.name) \
#text(size: 9.5pt, fill: rgb("#555555"), (data.contact.email, data.contact.phone, data.contact.location, ..data.contact.links).filter(present).join("  ·  "))
#v(-0.3em)
#line(length: 100%, stroke: 0.5pt + rgb("#9a9a9a"))
#v(0.8em)

#for p in data.paragraphs {
  let lines = p.split("\n")
  if p.starts-with("Subject:") {
    par(strong(p))
  } else if lines.len() > 1 {
    par({ for (i, l) in lines.enumerate() { if i > 0 { linebreak() }; l } })
  } else {
    par(p)
  }
}
