<script>
    let value = "World";
</script>
<h1>Hello {value}!</h1>

<label for="name">Name: </label><input type="text" id="name" bind:value />

<style>
    :global(body) {
        background-color: #301934;
    }

    h1 {
        font-size: 70px;
        font-weight: 600;
        color: #fdfdae;
        text-shadow: 0px 0px 5px #b393d3, 0px 0px 10px #b393d3, 0px 0px 10px #b393d3,
        0px 0px 20px #b393d3;
        background-clip: text;
        -webkit-background-clip: text;
    }

    label {
        color: white;
        font-size: 1.2rem;
    }

    input {
        border: 2px solid;
        border-radius: 4px;
        font-size: 1rem;
        margin: 0.25rem;
        min-width: 125px;
        padding: 0.5rem;
        transition: background-color 0.5s ease-out;
    }
</style>
