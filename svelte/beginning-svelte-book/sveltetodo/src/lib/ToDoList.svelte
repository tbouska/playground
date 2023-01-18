<script>
  import { TodoStore } from "../stores.js";
  import { Table, Button } from "sveltestrap";
  import { createEventDispatcher, onMount } from "svelte";
  import axios from "axios";
  import { scale } from "svelte/transition";

  const endpoint = "http://localhost:4000/todos/"

  onMount(async () => {
    try {
      const res = await axios.get(endpoint);
      TodoStore.update(() => {
        return res.data;
      });
    }
    catch(e){
      console.log("Failed to fetch data from API");
    }
  });

  const dispatch = createEventDispatcher();

  const handleToggleComplete = async (todo) => {
    todo.complete = !todo.complete;
    if(todo.complete === true){
      todo.dateCompleted = new Date().toDateString();
    } else {
      todo.dateCompleted = false;
    }

    await axios.patch(endpoint + todo.id,{complete: todo.complete, dateCompleted: todo.dateCompleted});

    TodoStore.update(currentTodos => {
      let updatedTodos = structuredClone(currentTodos);  // to avoid text reset after store update, when editTodo.text is emptied
      let updatedTodo = updatedTodos.find((item) => item.id === todo.id);
      updatedTodo = todo;
      return updatedTodos;
    });
  };

  const handleDelete = async (todoId) => {
    await axios.delete(endpoint + todoId);

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
    {#if !todo.complete}
      <tr out:scale>
        <td>{todo.text}</td>
        <td>{todo.date}</td>
        <td>
          <Button on:click={() => handleToggleComplete(todo)} color="success">Mark Complete</Button>
        </td>
        <td>
          <Button on:click={() => handleEdit(todo)}>Edit</Button>
        </td>
        <td>
          <Button on:click={() => handleDelete(todo.id)} color="danger">Delete</Button>
        </td>
      </tr>
    {/if}
  {/each}
  </tbody>
</Table>

{#if $TodoStore.filter(todo => todo.complete === true).length > 0}
<br />
<h2>Completed tasks</h2>
<Table>
  <thead>
    <tr>
      <th>To Do</th>
      <th>Date Completed</th>
      <th>Complete</th>
      <th>Delete</th>
    </tr>
  </thead>
  <tbody>
  {#each $TodoStore as todo (todo.id)}
    {#if todo.complete}
      <tr out:scale>
        <td>{todo.text}</td>
        <td>{todo.dateCompleted}</td>
        <td>
          <Button on:click={() => handleToggleComplete(todo)} color="success">Mark Incomplete</Button>
        </td>
        <td>
          <Button on:click={() => handleDelete(todo.id)} color="danger">Delete</Button>
        </td>
      </tr>
    {/if}
  {/each}
  </tbody>
</Table>
{/if}
