Component({
  properties: {
    recipe: { type: Object, value: {} },
    tagColor: { type: String, value: '' },
    tagText: { type: String, value: '' },
  },
  methods: {
    onTap() {
      this.triggerEvent('select', { id: this.data.recipe.id });
    },
  },
});
