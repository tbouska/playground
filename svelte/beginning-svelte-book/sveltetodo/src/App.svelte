<script>
  import ToDoList from "./lib/ToDoList.svelte";
  import ToDoForm from "./lib/ToDoForm.svelte";
  import ToDoEditForm from "./lib/ToDoEditForm.svelte";

  let editMode = false;
  let editTodo = null;

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
  <ToDoList on:edit-todo={handleEditTodo} />
</main>

<style>
  .mutation {
    margin-bottom: 3rem;
  }
</style>
