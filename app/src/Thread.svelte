<script>
import { onMount, tick } from 'svelte';
import { rgbToCss, hashString, timeSince, HSVtoRGB, trySetLSValue } from './utils';
import { Narrator } from './narrator';
import Username from './Username.svelte';
import UserNote from './UserNote.svelte';

let colors = new Set();
let colorsArr = [];


function getUsernameColor(username) {
	if (!username) return ["#000", "#fff"];

	const i = hashString(username);
	const [x, y, z] = [
		((i >> 16) & 0xFFFF) / (0xFFFF + 0.1),
		((i >> 8) & 0xFF) / 255.0,
		(i & 0xFF) / 256.0
	];

	let [r, g, b] = HSVtoRGB(
		x,
		y * 0.7 + 0.3,
		1.0,
	);
	r *= 255.0;
	g *= 255.0;
	b *= 255.0;

	const byBgColor = rgbToCss(r, g, b);
	if (!colors.has(username)) {
		colors.add(username);
		colorsArr.push([r, g, b, x]);
		colorsArr.sort((a, b) => a[3] - b[3]);
		colorsArr = colorsArr;
	}

	const byColor = (
		((r * 0.299 + g * 0.587 + b * 0.114) > 186) ? '#000' : '#fff'
	);

	return [byBgColor, byColor];
}

let colorScroll = [];
let totalScrollHeight = 0;
async function updateColorScroll(data) {
	if (!data) return;
	await tick();

	const out = [];

	// the first el is offset to the first comment
	const el = document.getElementById(`comment-${data[0].id}`);
	out.push({color: '', height: el.parentElement.offsetTop});

	for (let c of data) {
		const el = document.getElementById(`comment-${c.id}`);
		if (!el) {
			console.error(`Comment ${c.id} not found`);
			continue;
		};
		const elHeight = el.parentElement.offsetHeight;

		out.push({color: c.byBgColor, height: elHeight});
	}

	colorScroll = out;
	totalScrollHeight = document.documentElement.scrollHeight;
}
$: { updateColorScroll(data); }

function collapse(event, index) {
	let comment = data[index];
	let newValue = !comment.collapsed;
	comment.collapsed = newValue;

	let depth = comment.depth;
	index += 1;

	while (index < data.length) {
		let comment = data[index];
		index += 1;
		if (comment.depth <= depth) { break; }
		comment.collapsed = newValue;
	}

	data = data;
}

let currentlyReading = null;
let narrator = null;

async function handlePlayComment(commentIndex) {
	// TODO: stop on navigation?
	let comment = data[commentIndex];

	if (narrator && narrator.speaking) {
		const shouldStop = currentlyReading === comment.id;

		currentlyReading = null;
		narrator.stop();

		if (shouldStop) return;
	}

	currentlyReading = comment.id;

	const el = document.querySelector(`#comment-${comment.id} .comment-content`);
	const currentNarrator = new Narrator(
		window,
		el,
		new Promise((resolve) => {resolve("en-US")})
	);
	narrator = currentNarrator;
	window.currentNarrator = currentNarrator;
	const narratorRate = (
		"cfg-narrator-rate" in localStorage ?
			parseFloat(localStorage["cfg-narrator-rate"]) : 1.2
	);
	await currentNarrator.start({rate: narratorRate});

	if (currentlyReading === comment.id) {currentlyReading = null;}

	if (!currentNarrator._stopped) {  // if stopped by itself, go to the next comment
		// TODO: check not end of the thread
		handlePlayComment(commentIndex + 1).then(() => {});
	}
}

function handleNarratorPrev(e, i) {
	narrator.skipPrevious();
}

function handleNarratorNext(e, i) {
	narrator.skipNext();
}

// ###################################################################################

const isDev = (
	window.location.hostname === "localhost"
	|| localStorage["cfg-is-dev"] === "1"
);

export let threadId;
let usersById = {};
let opTweet = {};
let data = [];

const esc = (s) => {
  return s.replace(/[&<>"']/g, function(m) {
    switch (m) {
      case '&':
        return '&amp;';
      case '<':
        return '&lt;';
      case '>':
        return '&gt;';
      case '"':
        return '&quot;';
      case "'":
        return '&#039;';
	  default:
		return 'ERR';
    }
  });
};

const fetchData = async () => {
	const thread = await (await fetch(`/tree_${threadId}.json`)).json();
	opTweet = thread['tree'][0];

	const userList = Object.values(thread['users_by_id']);  // TODO: change dump format?
	const tempUsersById = {};
	userList.forEach(u => {
		tempUsersById[u.rest_id] = {
			id: u.rest_id,
			createdAt: new Date(u.legacy.created_at),
			username: u.legacy.screen_name,
			name: u.legacy.name,

			description: u.legacy.description,
			location: u.legacy.location,

			followingCount: u.legacy.friends_count,
			followersCount: u.legacy.followers_count,
		};
	});
	usersById = tempUsersById;

	const tempTree = thread['tree'].map(t => {
		const u = usersById[t.user_id_str];
		const username = u.username;
		const [byBgColor, byColor] = getUsernameColor(username);

		const [a, b] = t['display_text_range'];
		let text = t['full_text'].slice(a, b).trim();

		const date = new Date(t.created_at);

		const media = t?.extended_entities?.media || t?.entities?.media;
		
		// TODO: proper entitites parsing
		t.entities.urls.forEach(e => {
			text = text.replace(
				e.url,
				`<a href="${esc(e.expanded_url)}">${esc(e.expanded_url)}</a>`
			);
			text = text.replace('\ud83d\ude02', '😂');
		});

		// TODO: quoted tweet rendering

		return {
			// pad: [],
			depth: t._depth,

			_t: t,
			id: t.id_str,

			userId: t.user_id_str,
			userData: u,
			username,
			byColor,
			byBgColor,

			isOP: t.user_id_str === opTweet.user_id_str,

			favoriteCount: t.favorite_count,
			quoteCount: t.quote_count,
			retweetCount: t.retweet_count,

			formattedTime: date.toLocaleString("en-US"),
			timeAgo: timeSince(date),

			collapsed: false,
			text,

			media,
		};
	});

	let tweetStack = [];
	let prevDepth = 0;

	for(let t of tempTree) {
		t.pad = [];
		for(let i = 1; i < t.depth; i++) {
			t.pad.push({
				byBgColor: tweetStack[i].byBgColor,
				sameUser: tweetStack[i].username === t.username,
			});
		}

		if (t.depth == prevDepth) {
			tweetStack[t.depth] = t;  // replace if at the same level
		} else if (t.depth > prevDepth) {
			tweetStack.push(t);  // push if deeper
		} else if (t.depth < prevDepth) {
			tweetStack.length = t.depth;  // truncate to depth
			tweetStack.push(t); // push
		}

		prevDepth = t.depth;

		t.depth = Math.max(0, t.depth - 1);  // remove main tweet's pad
	}

	data = tempTree;
};

onMount(fetchData);
</script>

{#if data.length}
<div class="trx">
	<div class="colorScroll">
		{#each colorScroll as c, i}
			<div style="background: {c.color}; height: {c.height / totalScrollHeight * 100}%; width: 100%;"></div>
		{/each}
	</div>

	<div class="colors-bar">
		{#each colorsArr as c}
			<div style="background-color: {rgbToCss(...c)}; flex: 1; max-width: 6px"></div>
		{/each}
	</div>

<div class="thread-container">

<div class="comments" role="tree">
{#each data as c, i (c.id)}
	<div class='comment-container'>
		{#each {length: c.depth} as _, i}
			<div class='pad' style="background: {c.pad[i].byBgColor};">
				{#if c.pad[i].sameUser}
					<div
						class='pad-same-user'
						style="background-color: {c.byColor}; border-color: {c.byBgColor};"
					></div>
				{/if}
			</div>
		{/each}

		<div id="comment-{c.id}" class='comment' role="treeitem">
			<div class="comment-header">
				<Username data={c.userData} color={c.byColor} bgColor={c.byBgColor}/>
				{#if c.isOP}<div class="meta-gray">OP</div>{/if}
				<span class="date meta-gray" title="{c.formattedTime}">{c.timeAgo}</span>

				<button class="btn-text" on:click={(e) => collapse(e, i)} title="collapse">
					{#if c.collapsed}[+]{:else}[-]{/if}
				</button>
				<button class="btn-text" on:click={() => handlePlayComment(i)} title="text-to-speech">
					{#if currentlyReading === c.id}
						■&#xFE0E;
					{:else}
						▶&#xFE0E;
					{/if}
				</button>

				{#if currentlyReading === c.id}
				<button class="btn-text" on:click={(e) => handleNarratorPrev(e, i)} title="previous paragraph">
					⭠
				</button>
				<button class="btn-text" on:click={(e) => handleNarratorNext(e, i)} title="next paragraph">
					⭢
				</button>
				{/if}

				<div class="meta-gray"><UserNote id={c.userData.id} /></div>

				<div class="ml-auto"></div>

				<div class="meta-gray">
					{#if c.favoriteCount}♥{c.favoriteCount}{/if}
					{#if c.retweetCount} <span style="font-weight: 800;">↻</span>{c.retweetCount}{/if}
					{#if c.quoteCount} ❝{c.quoteCount}{/if}
				</div>

				<a class="no-vs" href={`https://twitter.com/${c.username}/status/${c.id}`} title="reply">
					&#10149;&#xFE0E;
				</a>
			</div>

			<div class="comment-content" class:d-none="{c.collapsed}">
				<p id="line-{c.id}">
					{@html c.text}
				</p>

				{#if c.media}
				<div>
					{#each c.media as m, mi (m.id_str)}
						{#if m.type === "photo"}
							<a href={m['media_url_https']}>
								<img class="attch" alt='' src={m['media_url_https']}/>
							</a>
						{:else if m.type === "video"}
							<!-- svelte-ignore a11y-media-has-caption -->
							<video class="attch" controls preload="metadata">
								{#each m.video_info.variants as v}
									<source src={v.url} type={v.content_type}>
								{/each}
							</video>
						{:else if m.type === "animated_gif"}
							<!-- svelte-ignore a11y-media-has-caption -->
							<video class="attch-gif" controls loop autoplay preload="metadata">
								{#each m.video_info.variants as v}
									<source src={v.url} type={v.content_type}>
								{/each}
							</video>
						{:else}
							<pre>{JSON.stringify(m)}</pre>
						{/if}
					{/each}
				</div>
				{/if}
			</div>
		</div>
	</div>
{/each}
<div style="height: 50vh;"></div>
</div>
</div>
</div>
{/if}

<style>

.attch {
	max-width: 100%;
	width: 100%;
	object-fit: contain;
	max-height: 400px;
}

.attch-gif {
	max-width: 100%;
	max-height: 150px;
}

:global(html, body) {
	background-color: var(--bg-color);
	color: var(--text-color);
}

:global(p) {
	margin: 0.5em 0 0.5em 0;

	line-height: 1.2;
	font-size: 1em;
}

:global(p:not(.quote)) {
	background: repeating-linear-gradient(
		#0000, 
		#0000 1.2em, 
		#0000000f 1.2em, 
		#0000000f 2.4em
	);
}

:global(.comment-content pre) {
	white-space: pre-wrap;
	margin: 0;
	line-height: 1.2rem;
}

.trx {
	display: flex;
	flex-direction: column;
}

.btn-text {
	display: inline-block;
	border: 0;
	background: none;
	margin: 0;
	padding: 0;

	cursor: pointer;
}

.colors-bar {
	display: flex;
	height: 10px;
	justify-content: center;
	margin: 5px 0;
}
.thread-container {
	z-index: 200;
}

@media only screen and (min-width: 900px) {
	.thread-container {
		min-width: 800px;
		margin-left: auto;
		margin-right: auto;
		width: max-content;
	}

	.comments .comment-container:first-child > .comment {
		width: 100%;
	}
}

.pad {
	margin-right: 3px;
	width: 5px;
	max-width: 5px;
	min-width: 5px;
}

.pad-same-user {
	width: 9px;
	height: 9px;
	border-radius: 50%;
	margin-top: 8.5px;
	border: 2px solid;
	left: -2px;
	position: relative;
}

.comment {
	border-radius: 5px;
	margin: 2px 0;

    width: 100%;
	max-width: min(62ch, 100vw);
	background-color: var(--comment-bg-color);
	overflow-wrap: anywhere;

	box-shadow: 0px 1px 6px #00000047;

	/* overflow: hidden; */
}

.comment-container {
	display: flex;
}

.comment-header * {
	text-decoration: none;
	white-space: nowrap;
}

.comment-header {
	margin: 0 5px 5px 0;
	display: flex;
	flex-wrap: wrap;
	align-items: center;
	gap: 10px;
}

.comment-header > * {
	display: block;
}

.comment-header > *:first-child {
	margin-left: 0;
}

.comment-header .ml-auto {
	margin-left: auto;
}

.meta-gray {
	font-size: 0.8em;
	color: var(--meta-color);
	font-weight: 300;
}

.comment-content {
	margin: 0 5px 5px 5px;
	overflow: auto;
}

:global(.comment-content a) {
	overflow-wrap: break-word;
	word-wrap: break-word;
	word-break: break-all;
	word-break: break-word;
}

:global(.comment-content > p:first-child) {
	margin-top: 0;
}

:global(.comment-content > p:last-child) {
	margin-bottom: 0;
}

.title {
	font-size: 1.2em;
}

.meta {
	color: var(--meta-color);
}

.meta, .story a {
	font-size: 0.8em;
    font-family: monospace;
}

:global(.quote) {
	background-color: rgba(0, 0, 0, 0.12);
	/* border-left: 4px solid rgba(0, 0, 0, 0.507); */
	border-left: 6px solid var(--text-color);
	padding: 5px 0 5px 12px;
}

.colorScroll {
	z-index: 100;

	position: fixed;
	top: 0;
	right: 0;

	width: 8px;
	height: 100%;

	display: flex;
	flex-direction: column;
}

@media only screen and (max-width: 899px) {
	.colorScroll {
		display: none;
	}
}
</style>
