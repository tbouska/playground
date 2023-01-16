<script>
  import { Alert, Button, Badge, Form, FormGroup, Input } from 'sveltestrap';

  let email = "";
  let password = "";
  let emailMessage = "";
  let passwordMessage = "";
  let validEmail = false;
  let validPassword = false;

  const handleSubmit = event => {
    event.preventDefault();
    handleEmailInput();
    handlePasswordInput();
    if(validEmail && validPassword){
      alert(`Email: ${email} \nPassword: ${password}`);
      email = "";
      password = "";
      validEmail = false;
      validPassword = false;
    }
  };

  const handleEmailInput = () => {
    validEmail = false;

    if (email.length < 6) {
      emailMessage = "Email should be minimum 6 characters";
    }
    else if (email.indexOf(" ") >= 0) {
      emailMessage = "Email cannot contain spaces";
    }
    else {
      emailMessage = "";
      validEmail = true;
    }
  }

  const handlePasswordInput = () => {
    validPassword = false;

    if (password.length < 6) {
      passwordMessage = "Password should be minimum 6 characters";
    }
    else if (password.indexOf(" ") >= 0) {
      passwordMessage = "Password cannot contain spaces";
    }
    else {
      passwordMessage = "";
      validPassword = true;
    }
  }
</script>

<Form on:submit={handleSubmit}>
  <FormGroup floating label="Enter email">
    <Input type="email" bind:value={email} />
  </FormGroup>

  {#if emailMessage.length > 0}
    <Alert color="danger">
      {emailMessage}
    </Alert>
  {/if}

  <FormGroup floating label="Enter password">
    <Input type="password" bind:value={password} />
  </FormGroup>

  {#if passwordMessage.length > 0}
    <Alert color="danger">
      {passwordMessage}
    </Alert>
  {/if}

  <Button type="submit" color="primary">Submit</Button>

</Form>

<p class="p-3 mt-3 border">
  Email: {email}
  <br />
  Password: {password}
</p>
