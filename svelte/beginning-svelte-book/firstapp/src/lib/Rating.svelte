<script>
  import { Icon } from 'sveltestrap'
  export let rating = 0;
  export let numOfReviews = 0;
  let color = "orange"
</script>

<span style="color: {color}" on:click={() => rating = 1}>
{#if rating >=1}
    <Icon name="star-fill" />
{:else}
    <Icon name="star" />
{/if}
</span>
<span style="color: {color}" on:click={() => rating = 2}>
{#if rating >=2}
    <Icon name="star-fill" />
{:else}
    <Icon name="star" />
{/if}
</span>
<span style="color: {color}" on:click={() => rating = 3}>
{#if rating >=3}
    <Icon name="star-fill" />
{:else}
    <Icon name="star" />
{/if}
</span>
<span style="color: {color}" on:click={() => rating = 4}>
{#if rating >=4}
    <Icon name="star-fill" />
{:else}
    <Icon name="star" />
{/if}
</span>
<span style="color: {color}" on:click={() => rating = 5}>
{#if rating >=5}
    <Icon name="star-fill" />
{:else}
    <Icon name="star" />
{/if}
<span style="color: black;">
{numOfReviews}
</span>
</span>
