export { default as platformApi } from "@/services/api/platform";
export { default as collectionApi } from "@/services/api/collection";
export { default as romApi } from "@/services/api/rom";
export { default as storeAuth } from "@/stores/auth";
export { default as storePlatforms, type Platform } from "@/stores/platforms";
export {
  default as storeCollections,
  type Collection,
  type CollectionType,
  type SmartCollection,
  type VirtualCollection,
} from "@/stores/collections";
