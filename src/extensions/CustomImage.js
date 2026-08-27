// TipTap image with size + align attributes and CSS classes
import Image from '@tiptap/extension-image'

export const CustomImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      size: {
        default: 'full', // 'full' | 'small'
        parseHTML: el => el.getAttribute('data-size') || 'full',
        renderHTML: attrs => ({
          'data-size': attrs.size,
          class:
            (attrs.size === 'small' ? 'tiptap-img-small' : 'tiptap-img-full') +
            (attrs.align ? ` tiptap-img-${attrs.align}` : ''),
        }),
      },
      align: {
        default: 'center', // 'left' | 'center' | 'right'
        parseHTML: el => el.getAttribute('data-align') || 'center',
        renderHTML: attrs => ({
          'data-align': attrs.align,
          class: `tiptap-img-${attrs.align}`,
        }),
      },
      alt: {
        default: '',
        parseHTML: el => el.getAttribute('alt') || '',
        renderHTML: attrs => ({ alt: attrs.alt }),
      },
      title: {
        // we’ll use 'title' to store a caption and render a <p> after insert
        default: '',
        parseHTML: el => el.getAttribute('title') || '',
        renderHTML: attrs => ({ title: attrs.title }),
      },
    }
  },
})
