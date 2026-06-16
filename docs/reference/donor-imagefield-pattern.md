# Donor reference — per-model `image_field` convention

Salvaged from the (now-deleted) donor repo **Open-Generative-AI** before deletion.
This is the one pattern kept from that repo's audit. **Reference-only — JavaScript, not ported.** The convention is already folded into `OPENMONTAGE_FACTORY_SPEC_v2.md` Systems A & F.

---

## 1. The pattern (plain language)

Different image / edit models expect the reference image under **different payload keys** — some want `image_url`, some want an array `images_list`, some use a bespoke name like `model_image_url` or `person_image_url`. Image-to-video models may also accept an **optional end-frame** under yet another key (e.g. `last_image`).

Instead of guessing the key (or silently stripping keys the model doesn't declare), **each model entry declares its image field(s) as metadata**, and the client fills that exact key:

- `imageField` — the payload key the reference image(s) go into.
- `lastImageField` (optional) — the payload key for an end-frame image.
- If the field is `images_list`, the client sends an **array** of URLs; otherwise it sends a **single URL** (`imagesList[0]`).
- Local files are uploaded to a hosted URL first, then the resulting URL is placed in the declared field.

This makes reference-image passing deterministic per model rather than a best-effort guess.

---

## 2. Verbatim donor snippets

### `src/lib/muapi.js` — `generateI2I` (~L239–259, full function)

```js
    async generateI2I(params) {
        const key = this.getKey();
        const modelInfo = getI2IModelById(params.model);
        const endpoint = modelInfo?.endpoint || params.model;
        const url = `${this.baseUrl}/api/v1/${endpoint}`;

        const finalPayload = {};

        // Only include prompt if the model supports it and one was provided
        finalPayload.prompt = params.prompt || '';

        // Place the uploaded image(s) in the correct field for this model
        const imageField = modelInfo?.imageField || 'image_url';
        const imagesList = params.images_list?.length > 0 ? params.images_list : (params.image_url ? [params.image_url] : null);
        if (imagesList) {
            if (imageField === 'images_list') {
                finalPayload.images_list = imagesList;
            } else {
                finalPayload[imageField] = imagesList[0];
            }
        }

        if (params.aspect_ratio) finalPayload.aspect_ratio = params.aspect_ratio;
        if (params.resolution) finalPayload.resolution = params.resolution;
        if (params.quality) finalPayload.quality = params.quality;

        console.log('[Muapi] I2I Request:', url);
        console.log('[Muapi] I2I Payload:', finalPayload);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': key },
                body: JSON.stringify(finalPayload)
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`API Request Failed: ${response.status} ${response.statusText} - ${errText.slice(0, 100)}`);
            }

            const submitData = await response.json();
            console.log('[Muapi] I2I Submit Response:', submitData);

            const requestId = submitData.request_id || submitData.id;
            if (!requestId) return submitData;

            if (params.onRequestId) params.onRequestId(requestId);

            const result = await this.pollForResult(requestId, key);
            const imageUrl = result.outputs?.[0] || result.url || result.output?.url;
            console.log('[Muapi] I2I Result URL:', imageUrl);
            return { ...result, url: imageUrl };
        } catch (error) {
            console.error('Muapi I2I Error:', error);
            throw error;
        }
    }
```

### `src/lib/muapi.js` — `generateI2V` (~L309–347, full function)

```js
    async generateI2V(params) {
        const key = this.getKey();
        const modelInfo = getI2VModelById(params.model);
        const endpoint = modelInfo?.endpoint || params.model;
        const url = `${this.baseUrl}/api/v1/${endpoint}`;

        const finalPayload = {};

        if (params.prompt) finalPayload.prompt = params.prompt;

        // Place image in the correct field for this model
        const imageField = modelInfo?.imageField || 'image_url';
        if (params.images_list && params.images_list.length > 0) {
            if (imageField === 'images_list') {
                finalPayload.images_list = params.images_list;
            } else {
                finalPayload[imageField] = params.images_list[0];
            }
        } else if (params.image_url) {
            if (imageField === 'images_list') {
                finalPayload.images_list = [params.image_url];
            } else {
                finalPayload[imageField] = params.image_url;
            }
        }

        // Optional end-frame image — only for models declaring lastImageField.
        // Server-side param name varies (last_image vs end_image_url).
        const lastImageField = modelInfo?.lastImageField;
        if (lastImageField && params.last_image) {
            if (lastImageField === 'images_list') {
                if (!finalPayload.images_list) finalPayload.images_list = [];
                if (finalPayload.images_list.indexOf(params.last_image) === -1) {
                    finalPayload.images_list.push(params.last_image);
                }
            } else {
                finalPayload[lastImageField] = params.last_image;
            }
        }

        if (params.aspect_ratio) finalPayload.aspect_ratio = params.aspect_ratio;
        if (params.duration) finalPayload.duration = params.duration;
        if (params.resolution) finalPayload.resolution = params.resolution;
        if (params.quality) finalPayload.quality = params.quality;
        if (params.mode) finalPayload.mode = params.mode;
        if (params.name) finalPayload.name = params.name;

        console.log('[Muapi] I2V Request:', url);
        console.log('[Muapi] I2V Payload:', finalPayload);

        try {
            const response = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'x-api-key': key },
                body: JSON.stringify(finalPayload)
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(`API Request Failed: ${response.status} ${response.statusText} - ${errText.slice(0, 100)}`);
            }

            const submitData = await response.json();
            console.log('[Muapi] I2V Submit Response:', submitData);

            const requestId = submitData.request_id || submitData.id;
            if (!requestId) return submitData;

            if (params.onRequestId) params.onRequestId(requestId);

            const result = await this.pollForResult(requestId, key, 900, 2000);
            const videoUrl = result.outputs?.[0] || result.url || result.output?.url;
            console.log('[Muapi] I2V Result URL:', videoUrl);
            return { ...result, url: videoUrl };
        } catch (error) {
            console.error('Muapi I2V Error:', error);
            throw error;
        }
    }
```

### `packages/studio/src/models.js` — example model entries (metadata headers; `inputs` block elided)

The entries below are quoted verbatim from the donor; only the long `inputs` schema blocks are elided (marked `...`) to show the metadata fields that carry the convention.

```js
  {
    "id": "flux-kontext-dev-i2i",
    "name": "Flux Kontext Dev I2I",
    "endpoint": "flux-kontext-dev-i2i",
    "family": "kontext",
    "imageField": "images_list",
    "hasPrompt": true,
    "maxImages": 10,
    "inputs": { ... }
  },
```

```js
  {
    "id": "ai-product-photography",
    "name": "AI Product Photography",
    "endpoint": "ai-product-photography",
    "family": "tools",
    "imageField": "person_image_url",
    "hasPrompt": true,
    "inputs": { ... }
  },
```

```js
  {
    "id": "kling-v2.1-master-i2v",
    "name": "Kling v2.1 Master I2V",
    "endpoint": "kling-v2.1-master-i2v",
    "family": "kling-v2.1",
    "imageField": "image_url",
    "lastImageField": "last_image",
    "hasPrompt": true,
    "inputs": { ... }
  },
```

These show all three variants: an **array** field (`images_list`, with `maxImages`), a **bespoke scalar** field (`person_image_url`), and a **scalar field plus an end-frame** (`image_url` + `lastImageField: "last_image"`).

---

## 3. Status

Reference-only (JavaScript, not ported). The convention is already folded into `OPENMONTAGE_FACTORY_SPEC_v2.md`:
- **System A** — image-capable model entries carry `image_field` (and optional `last_image_field`) in the structural map.
- **System F** — the image generation path fills that exact key (single URL for scalar fields, array for `images_list`) instead of relying on `image_selector`'s strip-on-mismatch behavior.
