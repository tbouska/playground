<script>
  import Products from './lib/Products.svelte'
  import Rating from './lib/Rating.svelte'
  import { Button } from 'sveltestrap'
</script>

<main>
  <Products />
  <Button color="danger">Click Me</Button>
  <Rating rating="1" />
  <Rating rating="3" />
</main>
