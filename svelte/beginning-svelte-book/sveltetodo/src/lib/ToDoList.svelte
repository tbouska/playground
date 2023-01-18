<script>
  import { TodoStore } from "../stores.js";
  import { Table, Button } from "sveltestrap";
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  const handleDelete = (todoId) => {
    TodoStore.update(currentTodos => {
      return currentTodos.filter(todo => todo.id != todoId)
    });
  };

  const handleEdit = (todo) => {
    dispatch("edit-todo", todo);
  };
</script>

<Table>
  <thead>
    <tr>
      <th>To Do</th>
      <th>Date Created</th>
      <th>Complete</th>
      <th>Edit</th>
      <th>Delete</th>
    </tr>
  </thead>
  <tbody>
  {#each $TodoStore as todo (todo.id)}
    <tr>
      <td>{todo.text}</td>
      <td>{todo.date}</td>
      <td>Mark Complete</td>
      <td>
        <Button on:click={() => handleEdit(todo)}>Edit</Button>
      </td>
      <td>
        <Button on:click={() => handleDelete(todo.id)} color="danger">Delete</Button>
      </td>
    </tr>
  {/each}
  </tbody>
</Table>
