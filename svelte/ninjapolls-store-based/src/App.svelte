<script>
  import Header from './lib/Header.svelte'
  import Footer from './lib/Footer.svelte'
  import Tabs from './lib/Tabs.svelte'
  import CreatePollForm from './lib/CreatePollForm.svelte'
  import PollList from './lib/PollList.svelte'

  const items = ["Current polls", "Create new poll"]
  let activeItem = "Current polls";

  const switchTab = (e) => {
    activeItem = e.detail;
  }

  const handleAddNewPoll = () => activeItem = "Current polls";
</script>

<Header />
<main>
  <Tabs {items} {activeItem} on:switchTab={switchTab} />
  {#if activeItem === "Current polls"}
    <PollList />
  {:else if activeItem === "Create new poll"}
    <CreatePollForm on:addNewPoll={handleAddNewPoll} />
  {/if}
</main>
  <Footer />

<style>
  main {
    max-width: 960px;
    margin: 40px auto;
  }
</style>
