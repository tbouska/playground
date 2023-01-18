<script>
  import ToDoList from "./lib/ToDoList.svelte";
  import ToDoForm from "./lib/ToDoForm.svelte";
</script>

<main>
  <div class="addTodoForm">
    <ToDoForm />
  </div>
  <ToDoList />
</main>

<style>
  .addTodoForm {
    margin-bottom: 3rem;
  }
</style>
