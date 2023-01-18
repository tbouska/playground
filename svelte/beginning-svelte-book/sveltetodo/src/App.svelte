<script>
  import ToDoList from "./lib/ToDoList.svelte";
  import ToDoForm from "./lib/ToDoForm.svelte";
  import ToDoEditForm from "./lib/ToDoEditForm.svelte";
  import { TodoStore } from "./stores.js";

  let editMode = false;
  let editTodo = null;

  $: count = $TodoStore.length;
  $: countPending = $TodoStore.filter(todo => todo.complete === false).length;
  $: countCompleted = $TodoStore.filter(todo => todo.complete === true).length;

  const handleEditTodo = (event) => {
    editMode = true;
    editTodo = event.detail;
  }
</script>

<main>
  {#if editMode}
  <div class="mutation">
    <ToDoEditForm on:edit-finished={() => editMode = false} editTodo={editTodo} />
  </div>
  {:else}
  <div class="mutation">
    <ToDoForm />
  </div>
  {/if}
  <br />
  <h4>Total Todos: {count} | Pending: {countPending} | Completed: {countCompleted}</h4>
  <br />
  <ToDoList on:edit-todo={handleEditTodo} />
</main>

<style>
  .mutation {
    margin-bottom: 3rem;
  }
</style>
