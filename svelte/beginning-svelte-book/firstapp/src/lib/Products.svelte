<script>
  import Product from './Product.svelte'
  let products = [
    {
      id: "1",
      imageUrl: "http://loremflickr.com/150/150?random=1",
      productName: "Product 1",
      releasedDate: "May 31, 2016",
      description: "Lorem ipsum dolor sit amet, consectetur...",
      rating: 4,
      numOfReviews: 2
    },
    {
      id: "2",
      imageUrl: "http://loremflickr.com/150/150?random=2",
      productName: "Product 2",
      releasedDate: "October 31, 2016",
      description: "Lorem ipsum dolor sit amet, consectetur...",
      rating: 2,
      numOfReviews: 12
    },
    {
      id: "3",
      imageUrl: "http://loremflickr.com/150/150?random=3",
      productName: "Product 3",
      releasedDate: "July 30, 2016",
      description: "Lorem ipsum dolor sit amet, consectetur...",
      rating: 5,
      numOfReviews: 2
    },
  ]
</script>

<h1>Products</h1>
{#if products.length > 0}
  {#each products as product (product.id)}
    <Product data={product} />
  {/each}
{:else}
  <p style="font-weight: bold;">No products to display</p>
{/if}
