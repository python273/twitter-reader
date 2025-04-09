<script>
function portal(el) {
  function destroy() {
    if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }

  document.body.appendChild(el);
  return {destroy};
}
</script>

<div use:portal>
  <slot />
</div>
