import json
from typing import Any, NotRequired, TypedDict, cast

import flask
from loguru import logger

from utils import indent

type Status = dict[str, Any]

type AssociativeResourceArray = dict[str, dict[str, "Resource"]]
"""
Represents an associative array used for conveniently representing a set of resources keyed by their type and name.

For example, a Pod named `my-pod` in the `my-namespace` namespace could be accessed as follows if the parent is
also in `my-namespace`:

    array["Pod.v1"]["my-pod"]

Alternatively, if the parent resource is cluster scoped, the Pod could be accessed as:

    array["Pod.v1"]["my-namespace/my-pod"]
"""


class ObjectMetadata(TypedDict):
    name: str
    namespace: NotRequired[str]
    uid: NotRequired[str]
    labels: NotRequired[dict[str, str]]
    annotations: NotRequired[dict[str, str]]
    # ...


class Resource(TypedDict):
    apiVersion: str
    kind: str
    metadata: ObjectMetadata


class DecoratorSyncRequest:
    """See https://metacontroller.github.io/metacontroller/api/decoratorcontroller.html#sync-hook-request."""

    class Type(TypedDict):
        controller: Resource
        """ The whole DecoratorController object, like what you might get from
        `kubectl get decoratorcontroller <name> -o json`. """

        object: Resource
        """ The target object, like what you might get from `kubectl get <target-resource> <target-name> -o json`. """

        attachments: AssociativeResourceArray
        """ An associative array of attachments that already exist. """

        related: AssociativeResourceArray
        """ An associative array of related objects that exists, if customize hook was specified. See the customize hook """

        finalizing: bool
        """ This is always false for the sync hook. See the finalize hook for details. """

    @staticmethod
    def load(data: dict[str, Any]) -> "DecoratorSyncRequest.Type":
        # TODO: Runtime validation?
        return cast(DecoratorSyncRequest.Type, data)


class DecoratorSyncResponse:
    """See https://metacontroller.github.io/metacontroller/api/decoratorcontroller.html#sync-hook-response."""

    class Type(TypedDict):
        labels: dict[str, str]
        """ A map of key-value pairs for labels to set on the target object. """

        annotations: dict[str, str]
        """ A map of key-value pairs for annotations to set on the target object. """

        status: NotRequired[Status | None]
        """ A JSON object that will completely replace the status field within the target object. Leave unspecified
        or null to avoid changing status. """

        attachments: list[Resource]
        """ A list of JSON objects representing all the desired attachments for this target object. """

        resyncAfterSeconds: float
        """ Set the delay (in seconds, as a float) before an optional, one-time, per-object resync. """

    @staticmethod
    def of(
        labels: dict[str, str] | None = None,
        annotations: dict[str, str] | None = None,
        status: Status | None = None,
        attachments: list[Resource] | None = None,
        resyncAfterSeconds: int = 0,
    ) -> "DecoratorSyncResponse.Type":
        return {
            "labels": labels or {},
            "annotations": annotations or {},
            "status": status,
            "attachments": attachments or [],
            "resyncAfterSeconds": resyncAfterSeconds,
        }


class DecoratorFinalizeRequest:
    """See https://metacontroller.github.io/metacontroller/api/decoratorcontroller.html#finalize-hook-request."""

    class Type(TypedDict):
        finalizing: bool
        """This is always true for the finalize hook. See the finalize hook for details."""

    @staticmethod
    def load(data: dict[str, Any]) -> "DecoratorFinalizeRequest.Type":
        # TODO: Runtime validation?
        return cast(DecoratorFinalizeRequest.Type, data)


class DecoratorFinalizeResponse:
    """See https://metacontroller.github.io/metacontroller/api/decoratorcontroller.html#finalize-hook-response."""

    class Type(TypedDict):
        finalized: bool
        """ A boolean indicating whether you are done finalizing. """

    def of(self, finalized: bool) -> "DecoratorFinalizeResponse.Type":
        return {"finalized": finalized}


class CompositeSyncRequest:
    """See https://metacontroller.github.io/metacontroller/api/compositecontroller.html#sync-hook-request."""

    class Type(TypedDict):
        controller: Resource
        """
        The whole CompositeController object, like what you might get from
        `kubectl get compositecontroller <name> -o json`.
        """

        parent: Resource
        """ The parent object, like what you might get from `kubectl get <parent-resource> <parent-name> -o json`. """

        children: AssociativeResourceArray
        """ An associative array of child objects that already exist. """

        related: AssociativeResourceArray
        """ An associative array of related objects that exists, if customize hook was specified. See the customize hook """

        finalizing: bool
        """ This is always false for the sync hook. See the finalize hook for details. """

    @staticmethod
    def load(data: dict[str, Any]) -> "CompositeSyncRequest.Type":
        # TODO: Runtime validation?
        return cast(CompositeSyncRequest.Type, data)


class CompositeSyncResponse:
    """See https://metacontroller.github.io/metacontroller/api/compositecontroller.html#sync-hook-response."""

    class Type(TypedDict):
        status: Status | None
        """
        A JSON object that will completely replace the status field within the parent object.

        What you put in status is up to you, but usually it's best to follow conventions established by controllers
        like Deployment. You should compute status based only on the children that existed when your hook was called;
        status represents a report on the last observed state, not the new desired state.
        """

        children: list[Resource]
        """ A list of JSON objects representing all the desired children for this parent object. """

        resyncAfterSeconds: float
        """ Set the delay (in seconds, as a float) before an optional, one-time, per-object resync. """

    @staticmethod
    def of(
        status: Status,
        children: list[Resource],
        resyncAfterSeconds: float = 0,
    ) -> "CompositeSyncResponse.Type":
        return {
            "status": status,
            "children": children or [],
            "resyncAfterSeconds": resyncAfterSeconds,
        }


class CompositeFinalizeRequest:
    """See https://metacontroller.github.io/metacontroller/api/compositecontroller.html#finalize-hook-request."""

    class Type(TypedDict):
        finalizing: bool
        """This is always true for the finalize hook. See the finalize hook for details."""

    @staticmethod
    def load(data: dict[str, Any]) -> "CompositeFinalizeRequest.Type":
        # TODO: Runtime validation?
        return cast(CompositeFinalizeRequest.Type, data)


class CompositeFinalizeResponse:
    """See https://metacontroller.github.io/metacontroller/api/compositecontroller.html#finalize-hook-response."""

    class Type(TypedDict):
        finalized: bool
        """ A boolean indicating whether you are done finalizing. """

    def of(self, finalized: bool) -> "CompositeFinalizeResponse.Type":
        return {"finalized": finalized}


class CustomizeRequest:
    """See https://metacontroller.github.io/metacontroller/api/customize.html#customize-hook-request."""

    class Type(TypedDict):
        controller: Resource
        """
        The whole CompositeController object, like what you might get from
        `kubectl get compositecontroller <name> -o json`.
        """

        parent: Resource
        """ The parent object, like what you might get from `kubectl get <parent-resource> <parent-name> -o json`. """

    @staticmethod
    def load(request: dict[str, Any]) -> "CustomizeRequest.Type":
        return cast(CustomizeRequest.Type, request)


class CustomizeResponse:
    """See https://metacontroller.github.io/metacontroller/api/customize.html#customize-hook-response."""

    class Type(TypedDict):
        relatedResources: list["ResourceRule"]
        """ A list of JSON objects (ResourceRules) representing all the desired related resource descriptions. """

    @staticmethod
    def of(relatedResources: list["ResourceRule"]) -> "CustomizeResponse.Type":
        return {"relatedResources": relatedResources}


_CustomizeRequest = CustomizeRequest
_CustomizeResponse = CustomizeResponse
type _CustomizeRequestType = CustomizeRequest.Type
type _CustomizeResponseType = CustomizeResponse.Type


class ResourceRule(TypedDict):
    """See https://metacontroller.github.io/metacontroller/api/customize.html#customize-hook-response."""

    apiVersion: str
    """
    The API `<group>/<version>` of the parent resource, or just <version> for core APIs. (e.g. `v1`,
    `apps/v1`, `batch/v1`).
    """

    resource: str
    """
    The canonical, lowercase, plural name of the parent resource. (e.g. `deployments`,
    `replicasets`, `statefulsets`).
    """

    labelSelector: NotRequired[dict[str, str]]
    """ A `v1.LabelSelector` object. Omit if not used (i.e. Namespace or Names should be used). """

    namespace: NotRequired[str]
    """ Optional. The Namespace to select in. """

    names: NotRequired[list[str]]
    """ Optional. A list of strings, representing individual objects to return. """


class DecoratorController:
    type CustomizeRequest = _CustomizeRequestType
    type CustomizeResponse = _CustomizeResponseType
    type SyncRequest = DecoratorSyncRequest.Type
    type SyncResponse = DecoratorSyncResponse.Type
    type FinalizeRequest = DecoratorFinalizeRequest.Type
    type FinalizeResponse = DecoratorFinalizeResponse.Type

    customize_request = staticmethod(_CustomizeRequest.load)
    customize_response = staticmethod(_CustomizeResponse.of)
    sync_request = staticmethod(DecoratorSyncRequest.load)
    sync_response = staticmethod(DecoratorSyncResponse.of)
    finalize_request = staticmethod(DecoratorFinalizeRequest.load)
    finalize_response = staticmethod(DecoratorFinalizeResponse.of)

    def customize(self, request: CustomizeRequest) -> CustomizeResponse:
        raise NotImplementedError

    def sync(self, request: SyncRequest) -> SyncResponse:
        raise NotImplementedError

    def finalize(self, request: FinalizeRequest) -> FinalizeResponse:
        raise NotImplementedError


class CompositeController:
    type CustomizeRequest = _CustomizeRequestType
    type CustomizeResponse = _CustomizeResponseType
    type SyncRequest = CompositeSyncRequest.Type
    type SyncResponse = CompositeSyncResponse.Type
    type FinalizeRequest = CompositeFinalizeRequest.Type
    type FinalizeResponse = CompositeFinalizeResponse.Type

    customize_request = staticmethod(_CustomizeRequest.load)
    customize_response = staticmethod(_CustomizeResponse.of)
    sync_request = staticmethod(CompositeSyncRequest.load)
    sync_response = staticmethod(CompositeSyncResponse.of)
    finalize_request = staticmethod(CompositeFinalizeRequest.load)
    finalize_response = staticmethod(CompositeFinalizeResponse.of)

    def customize(self, request: CustomizeRequest) -> CustomizeResponse:
        raise NotImplementedError

    def sync(self, request: SyncRequest) -> SyncResponse:
        raise NotImplementedError

    def finalize(self, request: FinalizeRequest) -> FinalizeResponse:
        raise NotImplementedError


def to_blueprint(controller: DecoratorController | CompositeController) -> flask.Blueprint:
    app = flask.Blueprint(type(controller).__name__, __name__)  # TODO: Bad import name?

    @app.route("/customize", methods=["POST"])
    def customize() -> flask.Response:
        assert isinstance(flask.request.json, dict)
        logger.debug("Customize Request:\n{}", indent(json.dumps(flask.request.json, indent=2)))
        response = controller.customize(controller.customize_request(flask.request.json))
        logger.debug("Customize Response:\n{}", indent(json.dumps(response, indent=2)))
        return flask.jsonify(response)

    @app.route("/sync", methods=["POST"])
    def sync() -> flask.Response:
        assert isinstance(flask.request.json, dict)
        logger.debug("Sync Request:\n{}", indent(json.dumps(flask.request.json, indent=2)))
        response = controller.sync(controller.sync_request(flask.request.json))  # type: ignore[arg-type]
        logger.debug("Sync Response:\n{}", indent(json.dumps(response, indent=2)))
        return flask.jsonify(response)

    return app
