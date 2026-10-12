#let data = json(bytes(sys.inputs.data))
#set page(paper: sys.inputs.at("paper", default: "a4"), margin: (x: 2.2cm, y: 2cm))
#set text(font: "Libertinus Serif", size: 11pt, lang: "en", hyphenate: false)
#set par(justify: false, leading: 0.6em, spacing: 1em)
#let present(x) = x != none and x != ""

#text(size: 16pt, weight: "bold", data.contact.name) \
#(data.contact.email, data.contact.phone, data.contact.location, ..data.contact.links).filter(present).join("  |  ")
#v(1.2em)
#for p in data.paragraphs { par(p) }
