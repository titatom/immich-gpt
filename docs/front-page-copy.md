# Front Page / Marketing Copy

This document contains ready-to-use copy for a future homepage, GitHub front page, and Reddit posts.

## Primary tagline

**AI-first metadata enrichment and album organization for Immich.**

## Hero section

### Headline

**Turn your Immich library into a searchable, structured photo archive with AI.**

### Subheadline

immich-gpt connects to your Immich server, analyzes assets one by one with AI, suggests better descriptions, tags, and album placement, and lets you review everything before anything is written back.

### Supporting points

- Self-hosted and built for Immich users
- AI-assisted metadata enrichment for descriptions and tags
- AI-assisted album and sub-album organization
- Human review before write-back
- Supports cloud and local model providers

## Short product description

immich-gpt helps you organize a growing Immich library without handing full control to automation. It pulls in your assets, prepares thumbnails server-side, combines visual context with existing metadata, and asks an AI model to suggest how each asset should be described, tagged, and organized. You stay in control through a review queue where every suggestion can be approved, edited, or rejected before it touches your Immich library.

## Feature section copy

### Enrich metadata with AI

Generate better descriptions and tags for photos already stored in Immich. Instead of leaving your library with missing or inconsistent metadata, immich-gpt creates suggestions you can quickly review and refine.

### Organize albums with AI assistance

Use buckets to define how assets should be grouped. Depending on the bucket mode, approved items can stay virtual, be mapped into an existing Immich album, be placed into AI-suggested sub-albums, or be moved to the Immich trash for clean-up workflows.

### Keep review in the loop

Nothing is silently pushed back into your library. Every result goes through a review step, so you can correct the bucket, rewrite the description, adjust tags, or change the album before approving write-back.

### Fit the workflow to your library

Run against your entire library, favourites only, or selected albums. Tune prompts, bucket priorities, confidence thresholds, and AI behavior so the app matches the way you already organize photos.

### Choose your AI provider

Use hosted models through OpenAI or OpenRouter, or keep everything local with Ollama. immich-gpt fetches thumbnails server-side so private Immich URLs are not sent directly to the AI provider.

## Three-step "How it works" section

1. **Sync assets from Immich**  
   Choose your scope: the full library, favourites, or selected albums.

2. **Let AI suggest metadata and organization**  
   The app classifies each asset, proposes descriptions and tags, and can suggest album or sub-album placement based on your bucket rules.

3. **Review, edit, and approve**  
   Approve suggestions one by one or in bulk, then write the final result back to Immich.

## GitHub-ready README intro

> immich-gpt is a self-hosted AI companion for Immich that helps you enrich metadata and organize your library without giving up control. It syncs assets from Immich, generates AI suggestions for descriptions, tags, and album placement, and routes everything through a review queue before write-back.

## GitHub-ready feature bullets

- Connects directly to your Immich library
- Suggests descriptions and tags with AI
- Supports AI-assisted album and sub-album organization
- Uses configurable buckets and prompts
- Lets you review, edit, approve, or reject every suggestion
- Works with OpenAI, OpenRouter, or local Ollama models
- Supports full-library, favourites-only, or album-specific workflows
- Keeps private Immich URLs away from external AI providers

## Reddit-ready post draft

### Title ideas

- I built an AI metadata and album organizer for Immich
- immich-gpt: AI-assisted descriptions, tags, and album organization for Immich
- A self-hosted "Paperless-style" AI workflow for Immich photos

### Post body

I have been building **immich-gpt**, a self-hosted app for people who want better metadata and cleaner album organization in Immich without fully automating away the review step.

The basic workflow is:

1. Connect immich-gpt to your Immich server
2. Sync assets from your whole library, favourites, or selected albums
3. Let AI suggest descriptions, tags, bucket classifications, and album/sub-album placement
4. Review every suggestion before anything is written back

What I wanted was something closer to a "review-first AI assistant" than a blind auto-tagging tool.

Some highlights:

- AI-generated descriptions and tags
- Bucket-based organization rules
- Album mapping and sub-album suggestions
- Bulk review and approval
- Support for OpenAI, OpenRouter, and Ollama
- Self-hosted workflow built specifically around Immich

The goal is to make large photo libraries easier to search and organize while keeping humans in control of the final result.

## Suggested future placement

- Use the **Hero section** and **Feature section copy** for a future landing page or expanded README front page.
- Use the **GitHub-ready README intro** and **feature bullets** for the repository front page.
- Use the **Reddit-ready post draft** as a launch or feedback post with minor edits for tone.
