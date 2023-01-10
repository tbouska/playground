<script>
  import Rating from './Rating.svelte';
  import {
    Image,
    Card,
    CardTitle,
    CardBody,
    CardSubtitle,
    CardText
  } from 'sveltestrap';

    export let data = {
      imageUrl: "",
      productName: "",
      releasedDate: "",
      rating: 0,
      numOfReviews: 0,
      description: "",
    };
</script>

<Card class="mb-3">
    <CardBody>
        <Image thumbnail alt="Landscape" src={data.imageUrl} />
        <CardTitle>{data.productName}</CardTitle>
        <CardSubtitle>{data.releasedDate}</CardSubtitle>
        <Rating rating={data.rating} numOfReviews={data.numOfReviews} />
        <CardText>
            {data.description}
        </CardText>
    </CardBody>
</Card>
