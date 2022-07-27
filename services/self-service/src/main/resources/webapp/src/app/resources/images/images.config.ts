/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

export enum Image_Table_Column_Headers {
  imageName = 'Image name',
  creationDate = 'Creation date',
  provider = 'Provider',
  imageStatus = 'Image status',
  sharedStatus = 'Shared status',
  templateName = 'Template name',
  instanceName = 'Instance name',
  actions = 'Actions',
}

export enum Shared_Status {
  shared = 'Shared',
  private = 'Private'
}

export const Image_Table_Titles = <const>[
  'checkbox',
  'imageName',
  'creationDate',
  'provider',
  'imageStatus',
  'sharedStatus',
  'templateName',
  'instanceName',
  'actions'
];

export enum Localstorage_Key {
  userName = 'user_name'
}

export enum Toaster_Message {
  successShare = 'The image has been shared with all current Regular Users on the project!'
}

export enum Placeholders {
  projectSelect = 'Select project'
}

export enum ImageStatuses {
  creating = 'CREATING',
  active = 'ACTIVE',
  failed = 'FAILED'
}

export enum TooltipStatuses {
  activeOnly = 'The image cannot be shared because it is not in the "Active" status',
  creatorOnly = 'Images may be shared by creators only',
  unableTerminate = 'Unable to terminate notebook because at least one compute is in progress'
}
