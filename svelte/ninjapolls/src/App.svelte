<script>
  import Header from './lib/Header.svelte'
  import Footer from './lib/Footer.svelte'
  import Tabs from './lib/Tabs.svelte'

  const items = ["Current polls", "Create new poll"]
  let activeItem = "Current polls";
  const switchTab = (e) => {
    activeItem = e.detail;
  }
</script>

<Header />
<main>
  <Tabs {items} {activeItem} on:switchTab={switchTab} />
  {#if activeItem === "Current polls"}
    <p>List of polls</p>
  {:else if activeItem === "Create new poll"}
    <p>Form to create a new poll</p>
  {/if}
</main>
  <Footer />

<style>
  main {
    max-width: 960px;
    margin: 40px auto;
  }
</style>
