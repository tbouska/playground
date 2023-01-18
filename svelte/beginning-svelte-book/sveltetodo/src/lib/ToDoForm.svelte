<script>
  import { v4 as uuidv4 } from "uuid";
  import { TodoStore } from "../stores.js";
  import { Form, FormGroup, Input, Alert, Button } from "sveltestrap";

  let text = "";
  let textErrorMessage = "";
  let validText = false;

  const handleSubmit = (event) => {
    event.preventDefault();
    handleInput();
    if(validText){
      const newTodo = {
        id: uuidv4(),
        text: text,
        complete: false,
        date: new Date().toDateString(),
        dateCompleted: false
      };

      TodoStore.update(currentTodos => {
        return [newTodo, ...currentTodos];
      });

      text = "";
      validText = false;
    }
  }

  const handleInput = () => {
    validText = false;
    if (text.length < 10) {
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
    <Input type="text" bind:value={text} />
  </FormGroup>
  {#if textErrorMessage.length > 0}
    <Alert color="danger">{textErrorMessage}</Alert>
  {/if}
  <Button type="submit" color="primary">Add Todo</Button>
</Form>
