/* generated using openapi-typescript-codegen -- do not edit */
/* istanbul ignore file */
/* tslint:disable */
/* eslint-disable */
import type { StorageRootHealthSchema } from "./StorageRootHealthSchema";
export type StorageRootSchema = {
  id: number;
  name: string;
  mode: string;
  active: boolean;
  created_at: string;
  updated_at: string;
  health: StorageRootHealthSchema;
};
