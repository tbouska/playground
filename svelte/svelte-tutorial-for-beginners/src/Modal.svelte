<script>
  export let showModal = false;
</script>

{#if showModal}
  <div class="backdrop" on:click|self>
    <div class="modal">
      <slot />
    </div>
  </div>
{/if}

<style>
  .backdrop {
    width: 100%;
    height: 100%;
    position: fixed;
    background: rgba(0,0,0,0.8);
  }
  .modal {
    width: 50rem;
    margin: 100px auto;
    background: white;
    border-radius:  15px;
  }
</style>
