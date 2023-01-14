<script>
  import PollStore from "../stores/PollStore.js";
  import { createEventDispatcher } from "svelte";
  import Button from "./Button.svelte"

  let fields = { question: "", answerA: "", answerB: "" };
  let errors = { question: "", answerA: "", answerB: "" };
  let valid = false;
  let submitAttempt = false;

  const dispatch = createEventDispatcher();

  $: {
    fields = fields;
    if (submitAttempt) {
      validateForm();
    }
  }

  const validateForm = () => {
    valid = true;

    if (fields.question.trim().length < 5) {
      valid = false;
      errors.question = "Question must be at least 5 characters long";
    } else {
      errors.question = "";
    }

    if (fields.answerA.trim().length < 1) {
      valid = false;
      errors.answerA = "Answer A cannot be empty";
    } else {
      errors.answerA = "";
    }

    if (fields.answerB.trim().length < 1) {
      valid = false;
      errors.answerB = "Answer B cannot be empty";
    } else {
      errors.answerB = "";
    }
  }

  const submitHandler = () => {
    submitAttempt = true;
    validateForm();

    if (valid) {
      let newPoll = {id: Math.random()*101|0, ...fields, votesA: 0, votesB: 0}
      PollStore.update(currentPolls => {
        return [...currentPolls, newPoll];
      });
      dispatch('addNewPoll');
    }
  }
</script>

<form on:submit|preventDefault={submitHandler}>
  <div class="form-field">
    <label for="question">Poll Question:</label>
    <input type="text" id="question" bind:value={fields.question}>
    <div class="error">{errors.question}</div>
  </div>
  <div class="form-field">
    <label for="answer-a">Answer A:</label>
    <input type="text" id="answer-a" bind:value={fields.answerA}>
    <div class="error">{errors.answerA}</div>
  </div>
  <div class="form-field">
    <label for="answer-b">Answer B:</label>
    <input type="text" id="answer-b" bind:value={fields.answerB}>
    <div class="error">{errors.answerB}</div>
  </div>
  <div class="form-footer">
    <Button flat type="secondary">Add poll</Button>
  </div>
</form>

<style>
  form {
    width: 400px;
    margin: 0 auto;
  }

  .form-field {
    margin: 18px auto;
    text-align: center;
  }

  input {
    width: 100%;
    border-radius: 6px;
    border: 2px solid #555;
    padding: 0.3rem;
    font-size: 0.9rem;
  }

  label {
    color: #555;
    margin: 10px auto;
    display: block;
    text-align: left;
  }

  .error {
    margin-top: 0.6rem;
    font-weight: bold;
    font-size: 0.8rem;;
    color: #d91b42;
  }

  .form-footer {
    text-align: center;
    margin-top: 2.5rem;
  }
</style>
