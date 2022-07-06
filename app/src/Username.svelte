<script>
import { timeSince, trySetLSValue } from "./utils";

export let data;
export let color;
export let bgColor;

const username = data.username;

let popup = false;

const userKey = `ur-${data.id}`;
const userNoteKey = `ur-n-${data.id}`;
let note = '';
let userRating = 9999;
let ratingColor = '';

function updateNote() {
	note = localStorage[userNoteKey] || '';
}
updateNote();

window.addEventListener('storage', (e) => {
	if (e.key === userNoteKey) updateNote();
});
window.addEventListener('c-update-user-note', (e) => {
	if (e.key === userNoteKey) updateNote();
}, false);

function onNoteChange() {
	localStorage[userNoteKey] = note;

	const event = new Event('c-update-user-note');
	event.key = userNoteKey;
	window.dispatchEvent(event);
}

function onNoteKeydown(event) {
	if (event.key === "Enter" || event.key === "Escape") {
		event.preventDefault();
		event.target.blur();
	}
}

function updateRating() {
	userRating = (parseInt(localStorage[userKey], 10) || 0);
	if (userRating === 0) {
		ratingColor = ''
	} else if (userRating < 0) {
		ratingColor = 'rgb(255, 32, 32)';
	} else {
		ratingColor = '#0f0';
	}
}
updateRating();

window.addEventListener('storage', (e) => {
	if (e.key === userKey) {
		updateRating();
	}
});
window.addEventListener('c-update-user-rating', (e) => {
	if (e.key === userKey) {
		updateRating();
	}
}, false);

const upvote = () => {
	const current = (parseInt(localStorage[userKey], 10) || 0);
	trySetLSValue(userKey, current + 1);

	const event = new Event('c-update-user-rating');
	event.key = userKey;
	window.dispatchEvent(event);
}

const downvote = () => {
	const current = (parseInt(localStorage[userKey], 10) || 0);
	trySetLSValue(userKey, current - 1);

	const event = new Event('c-update-user-rating');
	event.key = userKey;
	window.dispatchEvent(event);
}
</script>

<div class="username-container">
	<button
		on:click={() => {popup = !popup;}}
		class="username"
		style="color: {color}; background: {bgColor};"
	>
		{username}
	</button>

	<div class='rating'>
		<button on:click={upvote}>+</button>
		<span style="color: {ratingColor}; font-weight: {ratingColor ? 'bold': ''}">
			{(userRating + '').padStart(3, '\xa0')}
		</span>
		<button on:click={downvote}>-</button>
	</div>

	{#if popup}
	<div class="userPopup">
		<input
			class="note"
			placeholder="Add a note..."
			bind:value={note}
			on:change={onNoteChange}
			on:keydown={onNoteKeydown}
		/>

		<div class="meta">
			<div>
				<a href="https://twitter.com/{username}">
					{data.name}
				</a>
				{" | "}
				{#if data.location}
					location: {data.location}
					{" | "}
				{/if}
				following: {data.followingCount}
				{" | "}
				followers: {data.followersCount}
				{" | "}
				<span title="{data.createdAt.toLocaleString("en-US")}">
					joined: {timeSince(data.createdAt)}
				</span>
			</div>
		</div>

		<div class="userAbout">{data.description}</div>
	</div>
	{/if}
</div>

<style>
.username-container {
	position: relative;
}

.meta {
	color: var(--meta-color);
}

.meta {
	font-size: 0.9em;
    font-family: monospace;
}

.username {
	text-decoration: none;
	font-weight: 600;
	border-radius: 4px 0 4px 0;
	padding: 1px 4px 1px 4px;
	line-height: 1.1;

	user-select: text;
}

.userAbout {
	margin: 8px 0;
}

.userPopup {
	z-index: 1000;

	top: calc(1em + 8px);
	width: min(50ch, 100vw);
	box-shadow: rgba(0, 0, 0, 0.3) 0 10px 10px;

	position: absolute;

	background-color: var(--comment-bg-color);
	border: 1px solid var(--brand-color);

	border-radius: 8px;
	padding: 5px;
}

.note {
	display: block;
	width: 100%;
	margin-bottom: 1em;
}

.rating {
	color: var(--meta-color);
	display: inline-block;
	font-family: monospace;
	font-weight: 500;
}
</style>
