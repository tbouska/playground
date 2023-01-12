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
<main></main>

<style>
  .backdrop {
    width: 100%;
    height: 100%;
    position: fixed;
    background: rgba(0,0,0,0.8);
  }
  .modal {
    background: white;
    padding: 10px;
    margin: 10% auto;
    max-width: 20rem;
    margin: 100px auto;
    background: white;
    border-radius:  15px;
    text-align: center;
  }
</style>
