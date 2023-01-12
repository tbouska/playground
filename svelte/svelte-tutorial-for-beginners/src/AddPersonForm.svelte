<script>
  let name;
  let beltColor;
  let age;
  let skills = [];
  const allowedBeltColors = [
    "white",
    "yellow",
    "orange",
    "green",
    "blue",
    "brown",
    "black",
    "red",
  ]

  const handleSubmit = () => {
    console.log(name, beltColor, age, skills)
  }
</script>

<h3>Add a new person</h3>
<form on:submit|preventDefault={handleSubmit}>
  <input type="text" placeholder="name" bind:value={name}>
  <br />
  <input type="number" placeholder="age" bind:value={age}>
  <br />
  <br />
  <label>Skills:</label>
  <br />
  <input type="checkbox" bind:group={skills} value="fighting">fighting<br />
  <input type="checkbox" bind:group={skills} value="running">running<br />
  <input type="checkbox" bind:group={skills} value="sneaking">sneaking<br />
  <br />
  <label>Belt color:</label>
  <select bind:value={beltColor} style="background: #ccc">
    {#each allowedBeltColors as color}
      <option value="{color}" style="color: {color}">{color}</option>
    {/each}
  </select>
  <br />
  <button>Add Person</button>
</form>

<style>
  h3 {
    color: #559;
    font-weight: 800;
  }

  input {
    border-radius: 5px;
    border-color:#339;
    padding: 0.4rem;
    font-size: large;
    margin: 0.8rem 0.3rem 0rem 0rem;
  }

  button {
    margin: 1rem;
    border: solid #339;
    background: #66b;
    color: #eee;
    font-weight: bolder;
  }

  label {
    font-weight: bold;
  }
</style>
