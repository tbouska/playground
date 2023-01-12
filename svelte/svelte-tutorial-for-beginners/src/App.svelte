<script>
  import Modal from './Modal.svelte';

  let showModal = false;
  let people = [
    { name: "yoshi", beltColor: "black", age: 25, id: 1 },
    { name: "mario", beltColor: "orange", age: 45, id: 2 },
    { name: "luigi", beltColor: "brown", age: 35, id: 3 },
  ];

  const toggleModal = () => showModal = !showModal;

  const handleClick = (id) => {
    people = people.filter((person) => person.id != id);
  }
</script>


<Modal {showModal} on:click={toggleModal}>
  <h3>Add a new person</h3>
  <form>
    <input type="text" placeholder="name">
    <input type="text" placeholder="belt color">
    <button>Add Person</button>
  </form>
</Modal>
<main>
  <button on:click={toggleModal}>Open Modal</button>
  {#each people as person (person.id)}
    <div>
      <h4>{person.name}</h4>
      {#if person.beltColor === "black"}
        <p><strong>MASTER NINJA</strong></p>
      {/if}
      <p>{person.age} years old, {person.beltColor} belt.</p>
      <button on:click={() => handleClick(person.id)}>delete</button>
    </div>
  {/each}
</main>

<style>
</style>
