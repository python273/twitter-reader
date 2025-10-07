<script>
const { data } = $props()

let colorScroll = $state([])
let totalScrollHeight = $state(0)

async function updateColorScroll(data) {
  console.log('updateColorScroll')
  if (!data || data.length === 0) return

  const out = []

  // the first el is offset to the first comment
  const el = document.getElementById(`comment-${data[0].id}`)
  out.push({color: '', height: el.parentElement.offsetTop})

  for (let c of data) {
    c.collapsed
    const el = document.getElementById(`comment-${c.id}`)
    if (!el) {
      console.error(`Comment ${c.id} not found`)
      continue
    };
    const elHeight = el.parentElement.offsetHeight
    out.push({color: c.byBgColor, height: elHeight})
  }

  colorScroll = out
  totalScrollHeight = document.documentElement.scrollHeight
}
$effect(() => { updateColorScroll(data) })
</script>

<div class="colors-scroll">
  {#each colorScroll as c, i}
    <div style="background: {c.color}; height: {c.height / totalScrollHeight * 100}%; width: 100%;"></div>
  {/each}
</div>

<style>
@media only screen and (max-width: 899px) {
  .colors-scroll {
    display: none !important;
  }
}

.colors-scroll {
  z-index: 100;

  position: fixed;
  top: 0;
  right: 0;

  width: 8px;
  height: 100%;

  display: flex;
  flex-direction: column;
  contain: strict;
}
</style>
