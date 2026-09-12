import { Node, mergeAttributes } from '@tiptap/core';

export const IframeEmbed = Node.create({
  name: 'iframeEmbed',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      src: { default: null },
      title: { default: 'Embedded content' },
      height: { default: 400 },
    };
  },

  parseHTML() {
    return [{ tag: 'iframe[src]' }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      { class: 'iframe-embed-wrapper my-6 rounded-lg overflow-hidden border border-slate-200' },
      [
        'iframe',
        mergeAttributes(HTMLAttributes, {
          class: 'w-full',
          frameborder: '0',
          allowfullscreen: 'true',
          loading: 'lazy',
        }),
      ],
    ];
  },

  addCommands() {
    return {
      setIframeEmbed:
        (options) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs: options,
          }),
    };
  },
});
