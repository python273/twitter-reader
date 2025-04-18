/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this file,
 * You can obtain one at http://mozilla.org/MPL/2.0/. */

// Original source:
// https://github.com/mozilla/gecko-dev/blob/d36cf98aa85f24ceefd07521b3d16b9edd2abcb7/toolkit/components/narrate/Narrator.jsm
// https://github.com/mozilla/gecko-dev/blob/d36cf98aa85f24ceefd07521b3d16b9edd2abcb7/toolkit/themes/shared/narrate.css


// Maximum time into paragraph when pressing "skip previous" will go
// to previous paragraph and not the start of current one.
const PREV_THRESHOLD = 2000

export function Narrator(win, el, languagePromise) {
  this._el = el
  this._win = win
  this._doc = win.document
  this._languagePromise = languagePromise
  this._speechOptions = {}
  this._startTime = 0
  this._stopped = false
}

Narrator.prototype = {
  get _treeWalker() {
    if (!this._treeWalkerRef) {
    //   let wu = this._win.windowUtils;
      let nf = this._win.NodeFilter

      let filter = {
        _matches: new Set(),

        // We want high-level elements that have non-empty text nodes.
        // For example, paragraphs. But nested anchors and other elements
        // are not interesting since their text already appears in their
        // parent's textContent.
        acceptNode(node) {

          let n = node
          while (n) {
            if (n.classList && n.classList.contains('narrator-skip')) {
              return NodeFilter.FILTER_SKIP
            }
            n = n.parentElement
          }

          if (this._matches.has(node.parentNode)) {
            // Reject sub-trees of accepted nodes.
            return nf.FILTER_REJECT
          }

          if (!/\S/.test(node.textContent)) {
            // Reject nodes with no text.
            return nf.FILTER_REJECT
          }

          //   let bb = wu.getBoundsWithoutFlushing(node);
          //   if (!bb.width || !bb.height) {
          //     // Skip non-rendered nodes. We don't reject because a zero-sized
          //     // container can still have visible, "overflowed", content.
          //     return nf.FILTER_SKIP;
          //   }

          for (let c = node.firstChild; c; c = c.nextSibling) {
            if (c.nodeType == c.TEXT_NODE && /\S/.test(c.textContent)) {
              // If node has a non-empty text child accept it.
              this._matches.add(node)
              return nf.FILTER_ACCEPT
            }
          }

          return nf.FILTER_SKIP
        },
      }

      this._treeWalkerRef = new WeakMap()

      // We can't hold a weak reference on the treewalker, because there
      // are no other strong references, and it will be GC'ed. Instead,
      // we rely on the window's lifetime and use it as a weak reference.
      this._treeWalkerRef.set(
        this._win,
        this._doc.createTreeWalker(
          this._el,
          nf.SHOW_ELEMENT,
          filter,
          false
        )
      )
    }

    return this._treeWalkerRef.get(this._win)
  },

  get _timeIntoParagraph() {
    let rv = Date.now() - this._startTime
    return rv
  },

  get speaking() {
    return (
      this._win.speechSynthesis.speaking || this._win.speechSynthesis.pending
    )
  },

  _getVoice(voiceURI) {
    if (!this._voiceMap || !this._voiceMap.has(voiceURI)) {
      this._voiceMap = new Map(
        this._win.speechSynthesis.getVoices().map(v => [v.voiceURI, v])
      )
    }

    return this._voiceMap.get(voiceURI)
  },

  // _isParagraphInView(paragraph) {
  //   if (!paragraph) {
  //     return false;
  //   }

  //   let bb = paragraph.getBoundingClientRect();
  //   return bb.top >= 0 && bb.top < this._win.innerHeight;
  // },

  _nodeToText(node) {
    // return node.textContent;
    const out = []

    if (node.nodeName === 'A' && node.textContent.match(/https?:\/\//)) {
      if (node.textContent.length < 4) {
        out.push(''.padEnd(node.textContent.length))
      } else {
        out.push('LINK'.padEnd(node.textContent.length))
      }
      return out.join('')
    }

    for (let cn of node.childNodes) {
      if (cn.nodeName === "A" && node.textContent.match(/https?:\/\//)) {
        // Replace link with spaces, so indexes in string are preserved
        // for Highlighter to work correctly
        // out.push(cn.textContent.replaceAll(/./g, ' '));
        if (cn.textContent.length < 4) {
          out.push(''.padEnd(cn.textContent.length))
        } else {
          out.push('LINK'.padEnd(cn.textContent.length))
        }
      } else {
        out.push(cn.textContent)
      }
    }

    return out.join('')
  },

  _speakInner() {
    this._win.speechSynthesis.cancel()
    let tw = this._treeWalker
    let paragraph = tw.currentNode
    if (paragraph == tw.root) {
      return Promise.resolve()
    }

    let utterance = new this._win.SpeechSynthesisUtterance(
      this._nodeToText(paragraph)
    )
    // console.log('READING', utterance.text);
    utterance.rate = this._speechOptions.rate
    if (this._speechOptions.voice) {
      utterance.voice = this._speechOptions.voice
    } else {
      utterance.lang = this._speechOptions.lang
    }

    this._startTime = Date.now()

    let highlighter = new Highlighter(this._win, paragraph)

    return new Promise((resolve, reject) => {
      utterance.addEventListener("start", () => {
        paragraph.classList.add("narrating")
        let bb = paragraph.getBoundingClientRect()
        if (bb.top < 0 || bb.bottom > this._win.innerHeight) {
          paragraph.scrollIntoView({ behavior: "smooth", block: "start" })
        }
      })

      utterance.addEventListener("end", () => {
        if (!this._win) {
          // page got unloaded, don't do anything.
          console.log('page got unloaded, dont do anything.')
          return
        }

        highlighter.remove()
        paragraph.classList.remove("narrating")
        this._startTime = 0

        if (this._stopped) {
          // User pressed stopped.
          resolve()
        } else {
          tw.currentNode = tw.nextNode() || tw.root
          this._speakInner().then(resolve, reject)
        }
      })

      utterance.addEventListener("error", () => {
        console.log("speech synthesis failed")
        reject("speech synthesis failed")
      })

      utterance.addEventListener("boundary", e => {
        if (e.name != "word") {
          // We are only interested in word boundaries for now.
          return
        }

        if (e.charLength) {
          highlighter.highlight(e.charIndex, e.charLength)
        }
      })

      this._win.speechSynthesis.speak(utterance)
    })
  },

  start(speechOptions) {
    this._speechOptions = {
      rate: speechOptions.rate,
      voice: this._getVoice(speechOptions.voice),
    }

    this._stopped = false
    return this._languagePromise.then(language => {
      if (!this._speechOptions.voice) {
        this._speechOptions.lang = language
      }

      let tw = this._treeWalker
      // if (!this._isParagraphInView(tw.currentNode)) {
      //   tw.currentNode = tw.root;
      //   while (tw.nextNode()) {
      //     if (this._isParagraphInView(tw.currentNode)) {
      //       break;
      //     }
      //   }
      // }
      if (tw.currentNode == tw.root) {
        tw.nextNode()
      }

      return this._speakInner()
    })
  },

  stop() {
    this._stopped = true
    this._win.speechSynthesis.cancel()
  },

  skipNext() {
    this._win.speechSynthesis.cancel()
  },

  skipPrevious() {
    this._goBackParagraphs(this._timeIntoParagraph < PREV_THRESHOLD ? 2 : 1)
  },

  setRate(rate) {
    this._speechOptions.rate = rate
    /* repeat current paragraph */
    this._goBackParagraphs(1)
  },

  setVoice(voice) {
    this._speechOptions.voice = this._getVoice(voice)
    /* repeat current paragraph */
    this._goBackParagraphs(1)
  },

  _goBackParagraphs(count) {
    let tw = this._treeWalker
    for (let i = 0; i < count; i++) {
      if (!tw.previousNode()) {
        tw.currentNode = tw.root
      }
    }
    this._win.speechSynthesis.cancel()
  },
}

/**
 * The Highlighter class is used to highlight a range of text in a container.
 *
 * @param {Element} container a text container
 */
export function Highlighter(win, container) {
  this.win = win
  this.container = container
}

// All text-related style rules that we should copy over to the highlight node.
const kTextStylesRules = [
  "font-family",
  "font-kerning",
  "font-size",
  "font-size-adjust",
  "font-stretch",
  "font-variant",
  "font-weight",
  "line-height",
  "letter-spacing",
  "text-orientation",
  "text-transform",
  "word-spacing",
]

Highlighter.prototype = {
  /**
   * Highlight the range within offsets relative to the container.
   *
   * @param {Number} startOffset the start offset
   * @param {Number} length the length in characters of the range
   */
  highlight(startOffset, length) {
    let containerRect = this.container.getBoundingClientRect()
    let range = this._getRange(startOffset, startOffset + length)
    let rangeRects = range.getClientRects()
    let computedStyle = this.win.getComputedStyle(range.endContainer.parentNode)
    let nodes = this._getFreshHighlightNodes(rangeRects.length)

    let textStyle = {}
    for (let textStyleRule of kTextStylesRules) {
      textStyle[textStyleRule] = computedStyle[textStyleRule]
    }

    for (let i = 0; i < rangeRects.length; i++) {
      let r = rangeRects[i]
      let node = nodes[i]

      let style = Object.assign(
        {
          top: `${r.top - containerRect.top + r.height / 2}px`,
          left: `${r.left - containerRect.left + r.width / 2}px`,
          width: `${r.width}px`,
          height: `${r.height}px`,
        },
        textStyle
      )

      // Enables us to vary the CSS transition on a line change.
      node.classList.toggle("newline", style.top != node.dataset.top)
      node.dataset.top = style.top

      // Enables CSS animations.
      // node.classList.remove("animate");
      // this.win.requestAnimationFrame(() => {
      //   node.classList.add("animate");
      // });

      // Enables alternative word display with a CSS pseudo-element.
      node.dataset.word = range.toString()

      // Apply style
      node.style = Object.entries(style)
        .map(s => `${s[0]}: ${s[1]};`)
        .join(" ")
    }
  },

  /**
   * Releases reference to container and removes all highlight nodes.
   */
  remove() {
    for (let node of this._nodes) {
      node.remove()
    }

    this.container = null
  },

  /**
   * Returns specified amount of highlight nodes. Creates new ones if necessary
   * and purges any additional nodes that are not needed.
   *
   * @param {Number} count number of nodes needed
   */
  _getFreshHighlightNodes(count) {
    let doc = this.container.ownerDocument
    let nodes = Array.from(this._nodes)

    // Remove nodes we don't need anymore (nodes.length - count > 0).
    for (let toRemove = 0; toRemove < nodes.length - count; toRemove++) {
      nodes.shift().remove()
    }

    // Add additional nodes if we need them (count - nodes.length > 0).
    for (let toAdd = 0; toAdd < count - nodes.length; toAdd++) {
      let node = doc.createElement("div")
      node.className = "narrate-word-highlight"
      this.container.appendChild(node)
      nodes.push(node)
    }

    return nodes
  },

  /**
   * Create and return a range object with the start and end offsets relative
   * to the container node.
   *
   * @param {Number} startOffset the start offset
   * @param {Number} endOffset the end offset
   */
  _getRange(startOffset, endOffset) {
    let doc = this.container.ownerDocument
    let i = 0
    let treeWalker = doc.createTreeWalker(
      this.container,
      doc.defaultView.NodeFilter.SHOW_TEXT
    )
    let node = treeWalker.nextNode()

    function _findNodeAndOffset(offset) {
      do {
        let length = node.data.length
        if (offset >= i && offset <= i + length) {
          return [node, offset - i]
        }
        i += length
      } while ((node = treeWalker.nextNode()))

      // Offset is out of bounds, return last offset of last node.
      node = treeWalker.lastChild()
      return [node, node.data.length]
    }

    let range = doc.createRange()
    range.setStart(..._findNodeAndOffset(startOffset))
    range.setEnd(..._findNodeAndOffset(endOffset))

    return range
  },

  /*
   * Get all existing highlight nodes for container.
   */
  get _nodes() {
    return this.container.querySelectorAll(".narrate-word-highlight")
  },
}
