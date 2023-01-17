import { writable } from "svelte/store";

export const TodoStore = writable([
  {
    id: 1,
    text: "finishing writing Svelte book",
    complete: false,
    date: new Date().toDateString(),
    dateCompleted: null
  },
  {
    id: 2,
    text: "play with kids",
    complete: false,
    date: new Date().toDateString(),
    dateCompleted: null
  },
  {
    id: 3,
    text: "read bible",
    complete: false,
    date: new Date().toDateString(),
    dateCompleted: null
  }
]);
