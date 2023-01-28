<script>
    import axios from "axios";

    let text = "";
    let figlet = "";

    const submitHandler = async () => {
        try {
            const res = await axios.post(
                `http://172.24.37.40:8080/function/figlet`, text, {
                    mode: 'no-cors',
                    headers: {
                        'content-type': 'text/plain'
                    }
                }
            )
            figlet = res.data;
        } catch (e) {
            figlet = "";
        }
    }
</script>


<div class="figlet-container">
    <pre class="figlet">{figlet}</pre>
    <form on:submit|preventDefault={submitHandler}>
        <div class="form-field">
            <label for="text">Figlet from:</label>
            <input type="text" id="text" bind:value={text} placeholder="Text">
        </div>
    </form>
</div>

<style>
    :global(body) {
        background-color: #301934;
    }

    .figlet {
        background-color: #f5f4e7;
        white-space: pre-wrap;
        border-radius: 4px;
        font-weight: 900;
    }

    .figlet-container {
        max-width: 38rem;
        min-width: 38rem;
        text-align: center;
        margin: 0 auto;
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
