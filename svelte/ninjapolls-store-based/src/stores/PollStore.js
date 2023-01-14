import { writable } from "svelte/store";

const PollStore = writable([
  {
    id: 1,
    question: "Python or JavaScript?",
    answerA: "Python",
    answerB: "JavaScript",
    votesA: 15,
    votesB: 9
  },
  {
    id: 2,
    question: "Beer or wine?",
    answerA: "Beer",
    answerB: "Wine",
    votesA: 11,
    votesB: 10
  },
]);

export default PollStore;
