<script>
  import Header from './lib/Header.svelte'
  import Footer from './lib/Footer.svelte'
  import Tabs from './lib/Tabs.svelte'
  import CreatePollForm from './lib/CreatePollForm.svelte'
  import PollList from './lib/PollList.svelte'

  const items = ["Current polls", "Create new poll"]
  let activeItem = "Current polls";
  let polls = [
    {
      id: 1,
      question: "Python or JavaScript?",
      answerA: "Python",
      answerB: "JavaScript",
      votesA: 15,
      votesB: 9
    }
  ];

  const switchTab = (e) => {
    activeItem = e.detail;
  }

  const handleAddNewPoll = (e) => {
    const newPoll = e.detail;
    polls = [newPoll, ...polls];
    console.log(JSON.stringify(polls));
    activeItem = "Current polls";
  }

  const handleVote = (e) => {
    const {answer, id} = e.detail;
    let copiedPolls = [...polls];
    let upvotedPoll = copiedPolls.find((item) => item.id ===id)
    if (answer === "a") {
      upvotedPoll.votesA++;
    }
    if (answer === "b") {
      upvotedPoll.votesB++;
    }
    polls = copiedPolls;

  }
</script>

<Header />
<main>
  <Tabs {items} {activeItem} on:switchTab={switchTab} />
  {#if activeItem === "Current polls"}
    <PollList {polls} on:vote={handleVote} />
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
