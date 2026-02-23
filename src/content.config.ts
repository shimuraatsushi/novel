import { defineCollection, z } from 'astro:content';

const chapters = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    part: z.number().int().min(1).max(3),
    episode: z.number().int().min(1),
    publishedAt: z.date(),
    description: z.string().optional(),
  }),
});

export const collections = { chapters };
