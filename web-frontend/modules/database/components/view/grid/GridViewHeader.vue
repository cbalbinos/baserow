<template>
  <ul v-if="!tableLoading" class="header__filter header__filter--full-width">
    <li class="header__filter-item">
      <GridViewHide
        :view="view"
        :fields="fieldsAllowedToBeHidden"
        :read-only="readOnly"
        :store-prefix="storePrefix"
      ></GridViewHide>
    </li>
    <li class="header__filter-item header__filter-item--right">
      <ViewSearch
        :view="view"
        :fields="fields"
        :store-prefix="storePrefix"
        @refresh="$emit('refresh', $event)"
      ></ViewSearch>
    </li>
  </ul>
</template>

<script>
import { mapState } from 'vuex'

import GridViewHide from '@baserow/modules/database/components/view/grid/GridViewHide'
import ViewSearch from '@baserow/modules/database/components/view/ViewSearch'

export default {
  name: 'GridViewHeader',
  components: { GridViewHide, ViewSearch },
  props: {
    view: {
      type: Object,
      required: true,
    },
    fields: {
      type: Array,
      required: true,
    },
    readOnly: {
      type: Boolean,
      required: true,
    },
    storePrefix: {
      type: String,
      required: true,
    },
  },
  computed: {
    ...mapState({
      tableLoading: (state) => state.table.loading,
    }),
    fieldsAllowedToBeHidden() {
      return this.fields.filter((field) => !field.primary)
    },
  },
}
</script>
