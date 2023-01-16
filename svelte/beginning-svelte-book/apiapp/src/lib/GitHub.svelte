<script>
  import { onMount } from "svelte";
  import { Spinner, Table, Button, Form, FormGroup, Input } from "sveltestrap";
  import axios from "axios";

  let users = [];
  let searchTerm = "";
  let isLoading = false;

  const getData = async () => {
    try {
      const res = await axios.get(
        `https://api.github.com/search/users?q=${searchTerm}`
      );
      users = res.data.items;
      isLoading = false;
    } catch (e) {
    }
  };

  onMount(async () => getData());

  const handleSubmit = event => {
    event.preventDefault();
    isLoading = true;
    getData();
  };
</script>

<Form on:submit={handleSubmit}>
  <FormGroup floating label="Search">
    <Input type="text" bind:value={searchTerm} />
  </FormGroup>
  <Button type="submit" color="primary">Submit</Button>
</Form>
<br />
{#if isLoading}
  <div style="text-align: center;">
    <Spinner color="primary" />
  </div>
{/if}
<br />
<Table>
  <thead>
    <tr>
      <th>ID</th>
      <th>Avatar</th>
      <th>Login</th>
      <th>URL</th>
    </tr>
  </thead>
  <tbody>
    {#each users as user}
      <tr>
        <th scope="row">{user.id}</th>
        <td><img alt={user.login} src="{user.avatar_url}" width="75" height="75" /></td>
        <td>{user.login}</td>
        <td><a href="{user.html_url}">{user.html_url}</a></td>
      </tr>
    {/each}
  </tbody>
</Table>
