# xmsh – A Filesystem-Inspired Shell for XML and HTML Documents

:copyright: Harald Weber 2025

**xmsh** is an interactive command-line tool that lets you explore, navigate, and manipulate XML and HTML documents as if they were part of a virtual filesystem.

Inspired by Unix shells and structured document formats, it combines the familiarity of commands like `cd`, `ls`, and `mv` with the power of XPath and DOM traversal.

---

## 🧠 Concept

Structured documents like XML and HTML are tree-based — just like filesystems. `xmsh` leverages this metaphor to:

- Mount multiple documents into a virtual root (like `/doc1`, `/doc2`)
- Navigate elements using paths (`/doc1/html/body/div`)
- Inspect, edit, and move nodes with shell-style commands

Everything happens interactively, from a clean command prompt:

```bash
/doc1/html/body>
ls
# div p span

/doc1/html/body/div>
cat
# "Welcome to the site"

mv ./div ./footer/
```
