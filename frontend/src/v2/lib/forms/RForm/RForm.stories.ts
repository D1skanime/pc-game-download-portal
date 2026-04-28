import type { Meta, StoryObj } from "@storybook/vue3-vite";
import { ref } from "vue";
import RBtn from "../../primitives/RBtn/RBtn.vue";
import RTextField from "../RTextField/RTextField.vue";
import RForm from "./RForm.vue";

const meta: Meta<typeof RForm> = {
  title: "Forms/RForm",
  component: RForm,
  argTypes: {
    disableEnterSubmit: { control: "boolean" },
    disableScrollToError: { control: "boolean" },
  },
};

export default meta;

type Story = StoryObj<typeof RForm>;

export const Basic: Story = {
  args: {},
  render: (args) => ({
    components: { RForm, RTextField, RBtn },
    setup() {
      const valid = ref(false);
      const name = ref("");
      const email = ref("");
      const submitted = ref<string | null>(null);
      const nameRules = [(v: string) => !!v || "Name is required"];
      const emailRules = [
        (v: string) => !!v || "Email is required",
        (v: string) => /.+@.+\..+/.test(v) || "Email must be valid",
      ];
      function onSubmit() {
        submitted.value = `${name.value} <${email.value}>`;
      }
      return {
        args,
        valid,
        name,
        email,
        nameRules,
        emailRules,
        submitted,
        onSubmit,
      };
    },
    template: `
      <div style="width: 360px; padding: var(--r-space-5); background: var(--r-color-bg-elevated); border-radius: var(--r-radius-md);">
        <RForm v-bind="args" v-model="valid" @submit="onSubmit">
          <RTextField v-model="name" label="Name" :rules="nameRules" required />
          <div style="height: var(--r-space-3)" />
          <RTextField v-model="email" label="Email" :rules="emailRules" required />
          <div style="height: var(--r-space-4)" />
          <RBtn type="submit" color="primary" :disabled="!valid">Submit</RBtn>
          <p v-if="submitted" style="margin-top: var(--r-space-3); color: var(--r-color-success)">
            Submitted: {{ submitted }}
          </p>
        </RForm>
      </div>
    `,
  }),
};
