<script>
  import Modal from './Modal.svelte';
  import AddPersonForm from './AddPersonForm.svelte';

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

  const addPerson = (e) => {
    const newPerson = e.detail;
    people = [newPerson, ...people]
    showModal = false;
    console.log(newPerson.id);
  }
</script>


<Modal {showModal} on:click={toggleModal}>
  <AddPersonForm on:addPerson={addPerson} />
</Modal>
<main class="container">
  <div>
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
  </div>
</main>

<style>
  .container {
    width: 100%;
    margin: 10% auto;
    align-items: center;
    justify-content: center;
    text-align: center;
    display: flexbox;
  }
</style>
