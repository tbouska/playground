<script>
  import { TodoStore } from "../stores.js";
  import { Form, FormGroup, Input, Alert, Button } from "sveltestrap";
  import { createEventDispatcher } from "svelte";

  const dispatch = createEventDispatcher();

  export let editTodo = null;
  let textErrorMessage = "";
  let validText = false;

  const handleSubmit = (event) => {
    event.preventDefault();
    handleInput();
    if(validText){
      TodoStore.update(currentTodos => {
        let updatedTodos = structuredClone(currentTodos);  // to avoid text reset after store update, when editTodo.text is emptied
        let updatedTodo = updatedTodos.find((item) => item.id === editTodo.id);
        updatedTodo.text = editTodo.text;
        return updatedTodos;
      });

      editTodo.text = "";
      validText = false;
      dispatch("edit-finished");
    }
  }

  const handleInput = () => {
    validText = false;

    if(editTodo.length < 10) {
      textErrorMessage = "Todo text should be minimum 10 characters";
    }
    else {
      textErrorMessage = "";
      validText = true;

    }
  }
</script>

<Form on:submit={handleSubmit}>
  <FormGroup floating label="Enter Todo Text">
    <Input type="text" bind:value={editTodo.text} />
  </FormGroup>
  {#if textErrorMessage.length > 0}
    <Alert color="danger">{textErrorMessage}</Alert>
  {/if}
  <Button type="submit" color="primary">Update</Button>
</Form>
